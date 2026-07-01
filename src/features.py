from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from statistics import mean
from typing import Any

from src import taxonomy
from src.evidence import find_evidence_snippets, find_term_matches
from src.jd_signals import match_terms
from src.normalize import normalize_for_matching, normalize_location, normalize_title, normalize_whitespace
from src.scoring_config import get_experience_band


@dataclass
class CandidateTextBundle:
    profile_text: str
    career_text: str
    skills_text: str
    education_text: str
    certifications_text: str
    all_text: str


@dataclass
class ProfileFeatures:
    candidate_id: str
    current_title: str
    normalized_title: str
    title_category: str
    current_company: str
    current_industry: str
    location: str
    country: str
    location_category: str
    years_of_experience: float | None
    experience_band: str


@dataclass
class SkillFeatures:
    skill_names: list[str]
    skill_count: int
    expert_skill_count: int
    advanced_or_expert_skill_count: int
    avg_endorsements: float
    max_skill_duration_months: int
    expert_zero_duration_count: int
    retrieval_ranking_skill_hits: list[str]
    embedding_vector_skill_hits: list[str]
    evaluation_skill_hits: list[str]
    weak_ai_hype_skill_hits: list[str]
    non_target_ai_skill_hits: list[str]
    assessment_score_count: int
    avg_assessment_score: float | None


@dataclass
class CareerFeatures:
    role_titles: list[str]
    companies: list[str]
    industries: list[str]
    total_career_months: int
    service_company_count: int
    product_industry_count: int
    current_company_is_service: bool
    consulting_only_career: bool
    has_product_company_context: bool
    retrieval_ranking_hits: list[str]
    embedding_vector_hits: list[str]
    evaluation_hits: list[str]
    production_evidence_hits: list[str]
    weak_ai_hype_hits: list[str]
    non_target_ai_hits: list[str]
    career_evidence_snippets: list[str]


@dataclass
class RedrobRawFeatures:
    open_to_work: bool | None
    last_active_date: str
    recruiter_response_rate: float | None
    avg_response_time_hours: float | None
    notice_period_days: int | None
    willing_to_relocate: bool | None
    preferred_work_mode: str
    github_activity_score: float | None
    search_appearance_30d: int | None
    saved_by_recruiters_30d: int | None
    interview_completion_rate: float | None
    offer_acceptance_rate: float | None
    verified_email: bool | None
    verified_phone: bool | None
    linkedin_connected: bool | None
    verification_count: int


@dataclass
class DiagnosticFlags:
    wrong_role_title: bool
    target_title: bool
    adjacent_title: bool
    salary_range_invalid: bool
    platform_dates_invalid: bool
    has_keyword_stuffing_shape: bool
    has_real_retrieval_or_ranking_evidence: bool
    has_evaluation_evidence: bool
    has_production_evidence: bool
    likely_non_target_ai_only: bool


@dataclass
class CandidateFeatures:
    candidate_id: str
    text: CandidateTextBundle
    profile: ProfileFeatures
    skills: SkillFeatures
    career: CareerFeatures
    redrob: RedrobRawFeatures
    diagnostic_flags: DiagnosticFlags
    matched_signal_terms: dict[str, list[str]]


def build_candidate_text_bundle(candidate: dict[str, Any]) -> CandidateTextBundle:
    profile_parts: list[str] = []
    career_parts: list[str] = []
    skill_parts: list[str] = []
    education_parts: list[str] = []
    certification_parts: list[str] = []

    profile = candidate.get("profile")
    if isinstance(profile, dict):
        _append_values(
            profile_parts,
            profile,
            ["headline", "summary", "current_title", "current_company", "current_industry", "location"],
        )

    career_history = candidate.get("career_history")
    if isinstance(career_history, list):
        for item in career_history:
            if isinstance(item, dict):
                _append_values(career_parts, item, ["title", "company", "industry", "description"])

    skills = candidate.get("skills")
    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict):
                _append_text(skill_parts, skill.get("name"))
            else:
                _append_text(skill_parts, skill)

    education = candidate.get("education")
    if isinstance(education, list):
        for item in education:
            if isinstance(item, dict):
                _append_values(education_parts, item, ["degree", "field_of_study"])

    certifications = candidate.get("certifications")
    if isinstance(certifications, list):
        for item in certifications:
            if isinstance(item, dict):
                _append_text(certification_parts, item.get("name"))

    profile_text = _join(profile_parts)
    career_text = _join(career_parts)
    skills_text = _join(skill_parts)
    education_text = _join(education_parts)
    certifications_text = _join(certification_parts)
    all_text = _join([profile_text, career_text, skills_text, education_text, certifications_text])
    return CandidateTextBundle(
        profile_text=profile_text,
        career_text=career_text,
        skills_text=skills_text,
        education_text=education_text,
        certifications_text=certifications_text,
        all_text=all_text,
    )


def categorize_title(title: object) -> str:
    normalized = normalize_title(title)
    if not normalized:
        return "unknown"
    if _matches_any(normalized, taxonomy.WRONG_ROLE_TITLES):
        return "wrong_role"
    if _matches_any(normalized, taxonomy.STRONG_TARGET_TITLES):
        return "target"
    if _matches_any(normalized, taxonomy.ADJACENT_ENGINEERING_TITLES):
        return "adjacent"
    return "unknown"


def categorize_location(location: object, country: object, willing_to_relocate: object = None) -> str:
    normalized_location = normalize_location(location)
    normalized_country = normalize_for_matching(country)
    if not normalized_location and not normalized_country:
        return "unknown"
    if _matches_any(normalized_location, taxonomy.PREFERRED_LOCATIONS):
        return "preferred"
    if _matches_any(normalized_location, taxonomy.ACCEPTABLE_LOCATIONS):
        return "acceptable"
    if willing_to_relocate is True:
        return "relocation_possible"
    if normalized_country == "india":
        return "india_other"
    if normalized_country:
        return "outside_india"
    return "unknown"


def extract_profile_features(candidate: dict[str, Any]) -> ProfileFeatures:
    profile = candidate.get("profile")
    redrob = candidate.get("redrob_signals")
    profile = profile if isinstance(profile, dict) else {}
    redrob = redrob if isinstance(redrob, dict) else {}
    years = _number_or_none(profile.get("years_of_experience"))
    current_title = normalize_whitespace(profile.get("current_title"))

    return ProfileFeatures(
        candidate_id=normalize_whitespace(candidate.get("candidate_id")),
        current_title=current_title,
        normalized_title=normalize_title(current_title),
        title_category=categorize_title(current_title),
        current_company=normalize_whitespace(profile.get("current_company")),
        current_industry=normalize_whitespace(profile.get("current_industry")),
        location=normalize_whitespace(profile.get("location")),
        country=normalize_whitespace(profile.get("country")),
        location_category=categorize_location(
            profile.get("location"),
            profile.get("country"),
            redrob.get("willing_to_relocate"),
        ),
        years_of_experience=years,
        experience_band=get_experience_band(years)["label"],
    )


def extract_skill_features(candidate: dict[str, Any]) -> SkillFeatures:
    skill_items = candidate.get("skills")
    skill_items = skill_items if isinstance(skill_items, list) else []
    skill_names: list[str] = []
    endorsements: list[float] = []
    durations: list[int] = []
    expert_count = 0
    advanced_or_expert_count = 0
    expert_zero_duration_count = 0

    for skill in skill_items:
        if isinstance(skill, dict):
            name = normalize_whitespace(skill.get("name"))
            proficiency = normalize_for_matching(skill.get("proficiency"))
            duration = _int_or_none(skill.get("duration_months"))
            endorsement = _number_or_none(skill.get("endorsements"))
            if name:
                skill_names.append(name)
            if endorsement is not None:
                endorsements.append(endorsement)
            if duration is not None:
                durations.append(duration)
            if proficiency == "expert":
                expert_count += 1
                if duration == 0:
                    expert_zero_duration_count += 1
            if proficiency in {"advanced", "expert"}:
                advanced_or_expert_count += 1
        elif isinstance(skill, str):
            skill_names.append(normalize_whitespace(skill))

    skills_text = " ".join(skill_names)
    assessment_scores = _assessment_scores(candidate)
    return SkillFeatures(
        skill_names=skill_names,
        skill_count=len(skill_names),
        expert_skill_count=expert_count,
        advanced_or_expert_skill_count=advanced_or_expert_count,
        avg_endorsements=round(mean(endorsements), 2) if endorsements else 0.0,
        max_skill_duration_months=max(durations) if durations else 0,
        expert_zero_duration_count=expert_zero_duration_count,
        retrieval_ranking_skill_hits=find_term_matches(skills_text, taxonomy.CORE_RETRIEVAL_RANKING_TERMS),
        embedding_vector_skill_hits=find_term_matches(skills_text, taxonomy.EMBEDDING_VECTOR_TERMS),
        evaluation_skill_hits=find_term_matches(skills_text, taxonomy.EVALUATION_TERMS),
        weak_ai_hype_skill_hits=find_term_matches(skills_text, taxonomy.WEAK_AI_HYPE_TERMS),
        non_target_ai_skill_hits=find_term_matches(skills_text, taxonomy.NON_TARGET_AI_SPECIALTIES),
        assessment_score_count=len(assessment_scores),
        avg_assessment_score=round(mean(assessment_scores), 2) if assessment_scores else None,
    )


def extract_career_features(
    candidate: dict[str, Any],
    text: CandidateTextBundle | None = None,
    include_evidence: bool = True,
) -> CareerFeatures:
    text = text or build_candidate_text_bundle(candidate)
    career_history = candidate.get("career_history")
    career_history = career_history if isinstance(career_history, list) else []
    profile = candidate.get("profile")
    profile = profile if isinstance(profile, dict) else {}

    role_titles: list[str] = []
    companies: list[str] = []
    industries: list[str] = []
    total_months = 0
    for item in career_history:
        if not isinstance(item, dict):
            continue
        _append_text(role_titles, item.get("title"))
        _append_text(companies, item.get("company"))
        _append_text(industries, item.get("industry"))
        duration = _int_or_none(item.get("duration_months"))
        if duration:
            total_months += duration

    service_company_count = sum(1 for company in companies if _matches_any(company, taxonomy.SERVICE_COMPANY_NAMES))
    product_industry_count = sum(
        1 for industry in industries if _matches_any(industry, taxonomy.PRODUCT_COMPANY_INDUSTRIES)
    )
    current_company_is_service = _matches_any(profile.get("current_company"), taxonomy.SERVICE_COMPANY_NAMES)
    consulting_only_career = bool(companies) and service_company_count == len(companies) and product_industry_count == 0
    has_product_company_context = product_industry_count > 0
    snippet_terms = (
        taxonomy.CORE_RETRIEVAL_RANKING_TERMS
        + taxonomy.EMBEDDING_VECTOR_TERMS
        + taxonomy.EVALUATION_TERMS
        + taxonomy.PRODUCTION_EVIDENCE_TERMS
    )

    return CareerFeatures(
        role_titles=role_titles,
        companies=companies,
        industries=industries,
        total_career_months=total_months,
        service_company_count=service_company_count,
        product_industry_count=product_industry_count,
        current_company_is_service=current_company_is_service,
        consulting_only_career=consulting_only_career,
        has_product_company_context=has_product_company_context,
        retrieval_ranking_hits=find_term_matches(text.career_text, taxonomy.CORE_RETRIEVAL_RANKING_TERMS),
        embedding_vector_hits=find_term_matches(text.career_text, taxonomy.EMBEDDING_VECTOR_TERMS),
        evaluation_hits=find_term_matches(text.career_text, taxonomy.EVALUATION_TERMS),
        production_evidence_hits=find_term_matches(text.career_text, taxonomy.PRODUCTION_EVIDENCE_TERMS),
        weak_ai_hype_hits=find_term_matches(text.career_text, taxonomy.WEAK_AI_HYPE_TERMS),
        non_target_ai_hits=find_term_matches(text.career_text, taxonomy.NON_TARGET_AI_SPECIALTIES),
        career_evidence_snippets=find_evidence_snippets(text.career_text, snippet_terms, max_snippets=3)
        if include_evidence
        else [],
    )


def extract_redrob_raw_features(candidate: dict[str, Any]) -> RedrobRawFeatures:
    redrob = candidate.get("redrob_signals")
    redrob = redrob if isinstance(redrob, dict) else {}
    verification_values = [
        redrob.get("verified_email"),
        redrob.get("verified_phone"),
        redrob.get("linkedin_connected"),
    ]
    return RedrobRawFeatures(
        open_to_work=_bool_or_none(redrob.get("open_to_work_flag")),
        last_active_date=normalize_whitespace(redrob.get("last_active_date")),
        recruiter_response_rate=_number_or_none(redrob.get("recruiter_response_rate")),
        avg_response_time_hours=_number_or_none(redrob.get("avg_response_time_hours")),
        notice_period_days=_int_or_none(redrob.get("notice_period_days")),
        willing_to_relocate=_bool_or_none(redrob.get("willing_to_relocate")),
        preferred_work_mode=normalize_whitespace(redrob.get("preferred_work_mode")),
        github_activity_score=_number_or_none(redrob.get("github_activity_score")),
        search_appearance_30d=_int_or_none(redrob.get("search_appearance_30d")),
        saved_by_recruiters_30d=_int_or_none(redrob.get("saved_by_recruiters_30d")),
        interview_completion_rate=_number_or_none(redrob.get("interview_completion_rate")),
        offer_acceptance_rate=_number_or_none(redrob.get("offer_acceptance_rate")),
        verified_email=_bool_or_none(redrob.get("verified_email")),
        verified_phone=_bool_or_none(redrob.get("verified_phone")),
        linkedin_connected=_bool_or_none(redrob.get("linkedin_connected")),
        verification_count=sum(1 for value in verification_values if value is True),
    )


def extract_diagnostic_flags(
    candidate: dict[str, Any],
    features_so_far: dict[str, Any] | None = None,
) -> DiagnosticFlags:
    features_so_far = features_so_far or {}
    text = features_so_far.get("text") or build_candidate_text_bundle(candidate)
    profile = features_so_far.get("profile") or extract_profile_features(candidate)
    skills = features_so_far.get("skills") or extract_skill_features(candidate)
    career = features_so_far.get("career") or extract_career_features(candidate, text=text)

    redrob = candidate.get("redrob_signals")
    redrob = redrob if isinstance(redrob, dict) else {}
    salary_range_invalid = _salary_range_invalid(redrob.get("expected_salary_range_inr_lpa"))
    platform_dates_invalid = _date_before(redrob.get("last_active_date"), redrob.get("signup_date"))
    has_retrieval = bool(career.retrieval_ranking_hits)
    has_production = bool(career.production_evidence_hits)
    has_eval = bool(career.evaluation_hits or find_term_matches(text.profile_text, taxonomy.EVALUATION_TERMS))
    skill_signal_count = (
        len(skills.retrieval_ranking_skill_hits)
        + len(skills.embedding_vector_skill_hits)
        + len(skills.evaluation_skill_hits)
        + len(skills.weak_ai_hype_skill_hits)
        + len(skills.non_target_ai_skill_hits)
    )
    has_keyword_stuffing_shape = skill_signal_count >= 4 and not (has_retrieval or has_production)
    has_any_retrieval_or_eval = bool(
        career.retrieval_ranking_hits
        or career.embedding_vector_hits
        or career.evaluation_hits
        or skills.retrieval_ranking_skill_hits
        or skills.embedding_vector_skill_hits
        or skills.evaluation_skill_hits
    )

    return DiagnosticFlags(
        wrong_role_title=profile.title_category == "wrong_role",
        target_title=profile.title_category == "target",
        adjacent_title=profile.title_category == "adjacent",
        salary_range_invalid=salary_range_invalid,
        platform_dates_invalid=platform_dates_invalid,
        has_keyword_stuffing_shape=has_keyword_stuffing_shape,
        has_real_retrieval_or_ranking_evidence=has_retrieval and has_production,
        has_evaluation_evidence=has_eval,
        has_production_evidence=has_production,
        likely_non_target_ai_only=bool(career.non_target_ai_hits or skills.non_target_ai_skill_hits)
        and not has_any_retrieval_or_eval,
    )


def extract_candidate_features(
    candidate: dict[str, Any],
    include_evidence: bool = True,
    include_matched_signal_terms: bool = True,
) -> CandidateFeatures:
    text = build_candidate_text_bundle(candidate)
    profile = extract_profile_features(candidate)
    skills = extract_skill_features(candidate)
    career = extract_career_features(candidate, text=text, include_evidence=include_evidence)
    redrob = extract_redrob_raw_features(candidate)
    diagnostic_flags = extract_diagnostic_flags(
        candidate,
        {"text": text, "profile": profile, "skills": skills, "career": career},
    )
    return CandidateFeatures(
        candidate_id=profile.candidate_id,
        text=text,
        profile=profile,
        skills=skills,
        career=career,
        redrob=redrob,
        diagnostic_flags=diagnostic_flags,
        matched_signal_terms=match_terms(text.all_text) if include_matched_signal_terms else {},
    )


def candidate_features_to_flat_dict(features: CandidateFeatures) -> dict[str, Any]:
    snippets = features.career.career_evidence_snippets[:3]
    return {
        "candidate_id": features.candidate_id,
        "current_title": features.profile.current_title,
        "title_category": features.profile.title_category,
        "years_of_experience": features.profile.years_of_experience,
        "experience_band": features.profile.experience_band,
        "location_category": features.profile.location_category,
        "skill_count": features.skills.skill_count,
        "expert_skill_count": features.skills.expert_skill_count,
        "retrieval_ranking_skill_hit_count": len(features.skills.retrieval_ranking_skill_hits),
        "career_retrieval_ranking_hit_count": len(features.career.retrieval_ranking_hits),
        "career_embedding_vector_hit_count": len(features.career.embedding_vector_hits),
        "career_evaluation_hit_count": len(features.career.evaluation_hits),
        "production_evidence_hit_count": len(features.career.production_evidence_hits),
        "weak_ai_hype_hit_count": len(features.career.weak_ai_hype_hits)
        + len(features.skills.weak_ai_hype_skill_hits),
        "non_target_ai_hit_count": len(features.career.non_target_ai_hits)
        + len(features.skills.non_target_ai_skill_hits),
        "service_company_count": features.career.service_company_count,
        "product_industry_count": features.career.product_industry_count,
        "consulting_only_career": features.career.consulting_only_career,
        "open_to_work": features.redrob.open_to_work,
        "recruiter_response_rate": features.redrob.recruiter_response_rate,
        "notice_period_days": features.redrob.notice_period_days,
        "willing_to_relocate": features.redrob.willing_to_relocate,
        "verification_count": features.redrob.verification_count,
        "wrong_role_title": features.diagnostic_flags.wrong_role_title,
        "has_keyword_stuffing_shape": features.diagnostic_flags.has_keyword_stuffing_shape,
        "has_real_retrieval_or_ranking_evidence": features.diagnostic_flags.has_real_retrieval_or_ranking_evidence,
        "has_evaluation_evidence": features.diagnostic_flags.has_evaluation_evidence,
        "has_production_evidence": features.diagnostic_flags.has_production_evidence,
        "evidence_snippet_1": snippets[0] if len(snippets) > 0 else "",
        "evidence_snippet_2": snippets[1] if len(snippets) > 1 else "",
        "evidence_snippet_3": snippets[2] if len(snippets) > 2 else "",
    }


def compact_feature_summary(features: CandidateFeatures) -> str:
    return (
        f"{features.candidate_id} | {features.profile.current_title} | "
        f"{features.profile.title_category} | {features.profile.years_of_experience} yrs | "
        f"retrieval/ranking evidence: {_yes_no(features.diagnostic_flags.has_real_retrieval_or_ranking_evidence)} | "
        f"eval evidence: {_yes_no(features.diagnostic_flags.has_evaluation_evidence)} | "
        f"open_to_work: {str(features.redrob.open_to_work).lower()}"
    )


def _append_values(parts: list[str], source: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        _append_text(parts, source.get(key))


def _append_text(parts: list[str], value: object) -> None:
    normalized = normalize_whitespace(value)
    if normalized:
        parts.append(normalized)


def _join(parts: list[str]) -> str:
    return normalize_whitespace(" ".join(part for part in parts if part))


def _matches_any(value: object, terms: tuple[str, ...]) -> bool:
    normalized = f" {normalize_for_matching(value)} "
    return any(f" {term} " in normalized for term in _normalized_terms(terms))


def _number_or_none(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _assessment_scores(candidate: dict[str, Any]) -> list[float]:
    redrob = candidate.get("redrob_signals")
    if not isinstance(redrob, dict):
        return []
    scores = redrob.get("skill_assessment_scores")
    if not isinstance(scores, dict):
        return []
    return [float(value) for value in scores.values() if isinstance(value, (int, float))]


def _salary_range_invalid(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    minimum = _number_or_none(value.get("min"))
    maximum = _number_or_none(value.get("max"))
    return minimum is not None and maximum is not None and minimum > maximum


def _date_before(left: object, right: object) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    try:
        return date.fromisoformat(left) < date.fromisoformat(right)
    except ValueError:
        return False


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


@lru_cache(maxsize=128)
def _normalized_terms(terms: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for term in terms:
        value = normalize_for_matching(term)
        if value:
            normalized.append(value)
    return tuple(normalized)
