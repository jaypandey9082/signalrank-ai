from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src import taxonomy
from src.evidence import find_term_matches
from src.features import CandidateFeatures, extract_candidate_features
from src.scoring_config import (
    STATIC_FIT_WEIGHTS,
    get_experience_band,
    get_static_score_band,
)
from src.utils import round_score


@dataclass
class ComponentScore:
    name: str
    raw_score: float
    weight: float
    weighted_score: float
    evidence: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class StaticScorecard:
    candidate_id: str
    static_fit_score: float
    score_band: str
    components: list[ComponentScore]
    debug_flags: dict[str, bool]
    short_summary: str


def clamp01(value: float | int | None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def make_component(
    name: str,
    raw_score: float,
    weight: float,
    evidence: list[str] | None = None,
    notes: str = "",
) -> ComponentScore:
    raw = round_score(clamp01(raw_score), 6)
    weight_value = round_score(weight, 6)
    return ComponentScore(
        name=name,
        raw_score=raw,
        weight=weight_value,
        weighted_score=round_score(raw * weight_value, 6),
        evidence=evidence or [],
        notes=notes,
    )


def score_career_evidence(features: CandidateFeatures) -> ComponentScore:
    career = features.career
    flags = features.diagnostic_flags
    raw = 0.0
    raw += min(0.35, 0.12 * len(career.retrieval_ranking_hits))
    raw += min(0.25, 0.07 * len(career.production_evidence_hits))
    raw += min(0.15, 0.08 * len(career.embedding_vector_hits))
    raw += 0.15 if flags.target_title else 0.0
    raw += 0.10 if career.has_product_company_context else 0.0
    if flags.wrong_role_title and not flags.has_real_retrieval_or_ranking_evidence:
        raw = min(raw, 0.20)

    return make_component(
        "career_evidence",
        raw,
        STATIC_FIT_WEIGHTS["career_evidence"],
        evidence=career.career_evidence_snippets[:3],
        notes="Career evidence is prioritized over skills.",
    )


def score_retrieval_ranking(features: CandidateFeatures) -> ComponentScore:
    career = features.career
    skills = features.skills
    flags = features.diagnostic_flags
    career_hits = len(career.retrieval_ranking_hits)
    embedding_hits = len(career.embedding_vector_hits)
    skill_hits = len(skills.retrieval_ranking_skill_hits) + len(skills.embedding_vector_skill_hits)
    raw = 0.0
    raw += min(0.45, 0.16 * career_hits)
    raw += min(0.25, 0.12 * embedding_hits)
    raw += min(0.20, 0.05 * skill_hits)
    raw += 0.10 if flags.has_real_retrieval_or_ranking_evidence else 0.0
    if career_hits == 0 and embedding_hits == 0 and skill_hits > 0:
        raw = min(raw, 0.55)
    if flags.wrong_role_title and career_hits == 0:
        raw = min(raw, 0.30)

    evidence = career.retrieval_ranking_hits[:4] + career.embedding_vector_hits[:3]
    return make_component(
        "retrieval_ranking",
        raw,
        STATIC_FIT_WEIGHTS["retrieval_ranking"],
        evidence=evidence,
        notes="Career retrieval/ranking evidence counts more than skill-list matches.",
    )


def score_skills(features: CandidateFeatures) -> ComponentScore:
    skills = features.skills
    flags = features.diagnostic_flags
    raw = 0.0
    raw += min(0.35, 0.13 * len(skills.retrieval_ranking_skill_hits))
    raw += min(0.30, 0.11 * len(skills.embedding_vector_skill_hits))
    raw += min(0.15, 0.08 * len(skills.evaluation_skill_hits))
    raw += min(0.12, 0.015 * skills.advanced_or_expert_skill_count)
    if skills.avg_assessment_score is not None:
        raw += min(0.08, skills.avg_assessment_score / 100 * 0.08)

    if skills.weak_ai_hype_skill_hits and not flags.has_production_evidence:
        raw = min(raw + 0.03, 0.40)
    if skills.non_target_ai_skill_hits and not flags.has_real_retrieval_or_ranking_evidence:
        raw = min(raw, 0.55)
    if flags.has_keyword_stuffing_shape:
        raw = min(raw, 0.50)
    if flags.wrong_role_title and not flags.has_real_retrieval_or_ranking_evidence:
        raw = min(raw, 0.35)

    evidence = (
        skills.retrieval_ranking_skill_hits
        + skills.embedding_vector_skill_hits
        + skills.evaluation_skill_hits
    )[:6]
    return make_component(
        "skills",
        raw,
        STATIC_FIT_WEIGHTS["skills"],
        evidence=evidence,
        notes="Skills support fit but are capped when career evidence is missing.",
    )


def score_experience_fit(features: CandidateFeatures) -> ComponentScore:
    band = get_experience_band(features.profile.years_of_experience)
    evidence = [f"{features.profile.years_of_experience} years", f"band: {band['label']}"]
    return make_component(
        "experience_fit",
        band["score"],
        STATIC_FIT_WEIGHTS["experience_fit"],
        evidence=evidence,
        notes="Ideal range is roughly 6-8 years; 5-9 remains useful.",
    )


def score_product_company(features: CandidateFeatures) -> ComponentScore:
    career = features.career
    raw = 0.0
    raw += min(0.65, 0.25 * career.product_industry_count)
    raw += 0.20 if career.has_product_company_context else 0.0
    raw += 0.15 if not career.consulting_only_career and career.service_company_count == 0 else 0.0
    if career.consulting_only_career:
        raw = min(raw, 0.35)
    elif career.service_company_count and career.product_industry_count == 0:
        raw = min(raw, 0.55)

    evidence = career.industries[:4] + career.companies[:3]
    return make_component(
        "product_company",
        raw,
        STATIC_FIT_WEIGHTS["product_company"],
        evidence=evidence,
        notes="Service-company history is not rejected here; stronger penalties come later.",
    )


def score_location_fit(features: CandidateFeatures) -> ComponentScore:
    scores = {
        "preferred": 1.0,
        "acceptable": 0.85,
        "relocation_possible": 0.65,
        "india_other": 0.45,
        "outside_india": 0.20,
        "unknown": 0.30,
    }
    category = features.profile.location_category
    return make_component(
        "location_fit",
        scores.get(category, 0.30),
        STATIC_FIT_WEIGHTS["location_fit"],
        evidence=[features.profile.location, features.profile.country, f"category: {category}"],
        notes="Location is a logistics signal, not a hard filter.",
    )


def score_evaluation_experience(features: CandidateFeatures) -> ComponentScore:
    career_hits = features.career.evaluation_hits
    profile_hits = find_term_matches(features.text.profile_text, taxonomy.EVALUATION_TERMS)
    skill_hits = features.skills.evaluation_skill_hits
    raw = 0.0
    raw += min(0.65, 0.22 * len(career_hits))
    raw += min(0.20, 0.10 * len(profile_hits))
    raw += min(0.15, 0.05 * len(skill_hits))
    if features.diagnostic_flags.has_real_retrieval_or_ranking_evidence and (career_hits or profile_hits):
        raw += 0.15
    if not career_hits and skill_hits:
        raw = min(raw, 0.35)

    return make_component(
        "evaluation_experience",
        raw,
        STATIC_FIT_WEIGHTS["evaluation_experience"],
        evidence=(career_hits + profile_hits + skill_hits)[:6],
        notes="Ranking evaluation matters most when tied to career/profile evidence.",
    )


def score_education_signal(features: CandidateFeatures) -> ComponentScore:
    hits = find_term_matches(features.text.education_text, taxonomy.EDUCATION_SIGNAL_FIELDS)
    raw = min(1.0, 0.35 * len(hits))
    return make_component(
        "education_signal",
        raw,
        STATIC_FIT_WEIGHTS["education_signal"],
        evidence=hits,
        notes="Education has low weight compared with shipped career evidence.",
    )


def compute_static_scorecard(features: CandidateFeatures) -> StaticScorecard:
    components = [
        score_career_evidence(features),
        score_retrieval_ranking(features),
        score_skills(features),
        score_experience_fit(features),
        score_product_company(features),
        score_location_fit(features),
        score_evaluation_experience(features),
        score_education_signal(features),
    ]
    total = clamp01(sum(component.weighted_score for component in components))
    score = round_score(total, 6)
    band = get_static_score_band(score)
    debug_flags = features.diagnostic_flags.__dict__.copy()
    short_summary = _static_summary(score, features, components)
    return StaticScorecard(
        candidate_id=features.candidate_id,
        static_fit_score=score,
        score_band=band,
        components=components,
        debug_flags=debug_flags,
        short_summary=short_summary,
    )


def score_candidate(candidate: dict[str, Any]) -> StaticScorecard:
    return compute_static_scorecard(extract_candidate_features(candidate))


def scorecard_to_flat_dict(scorecard: StaticScorecard) -> dict[str, Any]:
    row: dict[str, Any] = {
        "candidate_id": scorecard.candidate_id,
        "static_fit_score": scorecard.static_fit_score,
        "score_band": scorecard.score_band,
        "short_summary": scorecard.short_summary,
    }
    for component in scorecard.components:
        row[f"{component.name}_raw"] = component.raw_score
        row[f"{component.name}_weighted"] = component.weighted_score
    for flag_name, value in scorecard.debug_flags.items():
        row[flag_name] = value
    return row


def component_evidence_text(scorecard: StaticScorecard, max_items: int = 5) -> str:
    evidence: list[str] = []
    for component in scorecard.components:
        for item in component.evidence:
            if item and item not in evidence:
                evidence.append(item)
            if len(evidence) >= max_items:
                return " | ".join(evidence)
    return " | ".join(evidence)


def _static_summary(
    score: float,
    features: CandidateFeatures,
    components: list[ComponentScore],
) -> str:
    strengths: list[str] = []
    by_name = {component.name: component for component in components}
    if by_name["career_evidence"].raw_score >= 0.65:
        strengths.append("strong career evidence")
    if by_name["retrieval_ranking"].raw_score >= 0.60:
        strengths.append("strong retrieval/ranking evidence")
    if features.profile.experience_band == "ideal":
        strengths.append("ideal experience band")
    if features.profile.location_category in {"preferred", "acceptable"}:
        strengths.append("preferred/acceptable location")
    if not strengths:
        strengths.append("limited static JD fit")
    return f"Static fit {score:.2f}: {', '.join(strengths)}."
