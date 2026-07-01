from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src import taxonomy
from src.features import CandidateFeatures, extract_candidate_features
from src.normalize import normalize_for_matching, normalize_whitespace
from src.redrob_scoring import compute_redrob_risk_flags, parse_iso_date
from src.schema import is_valid_candidate_id
from src.scoring_config import (
    TRAP_PENALTY_CAP,
    TRAP_PENALTY_WEIGHTS,
    get_trap_penalty_multiplier,
    get_trap_severity_band,
)
from src.utils import cap_list, parse_float, parse_int, round_score, safe_join


@dataclass
class TrapSignal:
    code: str
    label: str
    severity: str
    penalty: float
    evidence: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class TrapPenaltyScorecard:
    candidate_id: str
    total_penalty: float
    severity_band: str
    penalty_multiplier: float
    signals: list[TrapSignal]
    risk_flags: dict[str, bool]
    short_summary: str


def clamp_penalty(value: float | int | None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return 0.0
    return max(0.0, min(TRAP_PENALTY_CAP, float(value)))


def make_trap_signal(
    code: str,
    label: str,
    severity: str,
    penalty: float,
    evidence: list[str] | None = None,
    notes: str = "",
) -> TrapSignal:
    return TrapSignal(
        code=code,
        label=label,
        severity=severity,
        penalty=round_score(max(0.0, min(1.0, float(penalty))), 6),
        evidence=evidence or [],
        notes=notes,
    )


def has_any(values: list[str] | tuple[str, ...] | set[str]) -> bool:
    return bool(values)


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def detect_wrong_role_keyword_stuffing(
    candidate: dict[str, Any],
    features: CandidateFeatures,
) -> list[TrapSignal]:
    if not features.diagnostic_flags.wrong_role_title:
        return []

    skill_hits = _ai_skill_hits(features)
    has_real_evidence = features.diagnostic_flags.has_real_retrieval_or_ranking_evidence
    if features.diagnostic_flags.has_keyword_stuffing_shape:
        return [
            make_trap_signal(
                "wrong_role_keyword_stuffing",
                "Wrong-role AI keyword stuffing",
                "high",
                TRAP_PENALTY_WEIGHTS["wrong_role_keyword_stuffing"],
                evidence=[
                    f"title={features.profile.current_title}",
                    f"title_category={features.profile.title_category}",
                    f"skill_hits={safe_join(cap_list(skill_hits, 6))}",
                    "no real career retrieval/ranking evidence",
                ],
                notes="Wrong-role profiles should not rank highly from AI skill keywords alone.",
            )
        ]

    if skill_hits and not has_real_evidence:
        return [
            make_trap_signal(
                "wrong_role_keyword_stuffing",
                "Wrong-role profile with AI skill claims",
                "medium",
                TRAP_PENALTY_WEIGHTS["wrong_role_keyword_stuffing"] * 0.65,
                evidence=[
                    f"title={features.profile.current_title}",
                    f"skill_hits={safe_join(cap_list(skill_hits, 5))}",
                ],
            )
        ]

    if has_real_evidence:
        return []
    return [
        make_trap_signal(
            "wrong_role_keyword_stuffing",
            "Wrong-role title without supporting retrieval career evidence",
            "low",
            TRAP_PENALTY_WEIGHTS["wrong_role_keyword_stuffing"] * 0.35,
            evidence=[f"title={features.profile.current_title}"],
        )
    ]


def detect_weak_ai_hype_without_production(
    candidate: dict[str, Any],
    features: CandidateFeatures,
) -> list[TrapSignal]:
    weak_hype = features.skills.weak_ai_hype_skill_hits + features.career.weak_ai_hype_hits
    profile_weak_hype = [
        term
        for term in taxonomy.WEAK_AI_HYPE_TERMS
        if f" {normalize_for_matching(term)} " in f" {normalize_for_matching(features.text.profile_text)} "
    ]
    weak_hype.extend(term for term in profile_weak_hype if term not in weak_hype)
    if not weak_hype:
        return []
    if (
        features.diagnostic_flags.has_production_evidence
        or features.diagnostic_flags.has_real_retrieval_or_ranking_evidence
        or features.diagnostic_flags.has_evaluation_evidence
    ):
        return []

    severity = "high" if features.profile.title_category in {"wrong_role", "adjacent"} else "medium"
    multiplier = 1.0 if severity == "high" else 0.75
    return [
        make_trap_signal(
            "weak_ai_hype_without_production",
            "Weak AI hype without production evidence",
            severity,
            TRAP_PENALTY_WEIGHTS["weak_ai_hype_without_production"] * multiplier,
            evidence=[
                f"hype_terms={safe_join(cap_list(weak_hype, 6))}",
                f"title_category={features.profile.title_category}",
            ],
            notes="The JD explicitly warns that recent AI-tool projects are not enough.",
        )
    ]


def detect_consulting_only_no_product(
    candidate: dict[str, Any],
    features: CandidateFeatures,
) -> list[TrapSignal]:
    service_industry_terms = ("it services", "consulting", "professional services", "outsourcing")
    service_industry_count = sum(
        1
        for industry in features.career.industries
        if any(term in normalize_for_matching(industry) for term in service_industry_terms)
    )
    service_company_hint_count = sum(
        1
        for company in features.career.companies
        if any(term in normalize_for_matching(company) for term in ("consulting", "services", "solutions"))
    )
    service_shaped_career = bool(features.career.companies) and (
        features.career.consulting_only_career
        or service_industry_count == len(features.career.industries)
        or service_company_hint_count == len(features.career.companies)
    )
    if not service_shaped_career:
        return []
    if features.career.product_industry_count > 0 or features.diagnostic_flags.has_real_retrieval_or_ranking_evidence:
        return []
    severity = "high" if features.career.current_company_is_service or service_industry_count else "medium"
    multiplier = 1.0 if severity == "high" else 0.75
    return [
        make_trap_signal(
            "consulting_only_no_product",
            "Consulting-only career with no product retrieval evidence",
            severity,
            TRAP_PENALTY_WEIGHTS["consulting_only_no_product"] * multiplier,
            evidence=[
                f"companies={safe_join(cap_list(features.career.companies, 5))}",
                f"industries={safe_join(cap_list(features.career.industries, 5))}",
            ],
            notes="Service-company history is not fatal, but the JD prefers product ML/retrieval ownership.",
        )
    ]


def detect_non_target_ai_only(
    candidate: dict[str, Any],
    features: CandidateFeatures,
) -> list[TrapSignal]:
    non_target_hits = features.skills.non_target_ai_skill_hits + features.career.non_target_ai_hits
    if not non_target_hits:
        return []
    has_retrieval_or_eval = bool(
        features.career.retrieval_ranking_hits
        or features.career.embedding_vector_hits
        or features.career.evaluation_hits
        or features.skills.retrieval_ranking_skill_hits
        or features.skills.embedding_vector_skill_hits
        or features.skills.evaluation_skill_hits
    )
    if has_retrieval_or_eval:
        return [
            make_trap_signal(
                "non_target_ai_only",
                "Non-target AI specialty with some retrieval evidence",
                "low",
                TRAP_PENALTY_WEIGHTS["non_target_ai_only"] * 0.35,
                evidence=[f"non_target_terms={safe_join(cap_list(non_target_hits, 5))}"],
            )
        ]
    return [
        make_trap_signal(
            "non_target_ai_only",
            "Non-target AI specialty without retrieval/evaluation evidence",
            "medium",
            TRAP_PENALTY_WEIGHTS["non_target_ai_only"],
            evidence=[f"non_target_terms={safe_join(cap_list(non_target_hits, 5))}"],
            notes="CV/speech/robotics-only profiles are weaker for this NLP/IR-heavy JD.",
        )
    ]


def detect_expert_skill_zero_duration(
    candidate: dict[str, Any],
    features: CandidateFeatures,
) -> list[TrapSignal]:
    skills = candidate.get("skills")
    if not isinstance(skills, list):
        return []
    zero_duration_experts: list[str] = []
    tiny_duration_experts: list[str] = []
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        proficiency = normalize_for_matching(skill.get("proficiency"))
        duration = parse_int(skill.get("duration_months"))
        name = normalize_whitespace(skill.get("name"))
        if proficiency == "expert" and duration == 0:
            zero_duration_experts.append(name)
        if proficiency == "expert" and duration is not None and 0 < duration <= 3:
            tiny_duration_experts.append(name)

    suspicious_count = len(zero_duration_experts)
    if suspicious_count == 0 and not (
        len(tiny_duration_experts) >= 4 and not features.diagnostic_flags.has_real_retrieval_or_ranking_evidence
    ):
        return []

    if suspicious_count >= 4 or (features.diagnostic_flags.wrong_role_title and suspicious_count >= 2):
        severity = "high"
        penalty = TRAP_PENALTY_WEIGHTS["expert_skill_zero_duration"]
    elif suspicious_count >= 2:
        severity = "medium"
        penalty = TRAP_PENALTY_WEIGHTS["expert_skill_zero_duration"] * 0.75
    else:
        severity = "low"
        penalty = TRAP_PENALTY_WEIGHTS["expert_skill_zero_duration"] * 0.45

    evidence = cap_list(zero_duration_experts + tiny_duration_experts, 6)
    return [
        make_trap_signal(
            "expert_skill_zero_duration",
            "Expert skill duration inconsistency",
            severity,
            penalty,
            evidence=[f"suspicious_skills={safe_join(evidence)}"],
        )
    ]


def detect_profile_data_inconsistency(
    candidate: dict[str, Any],
    features: CandidateFeatures,
) -> list[TrapSignal]:
    issues: list[str] = []
    if not is_valid_candidate_id(candidate.get("candidate_id")):
        issues.append("candidate_id missing or malformed")

    redrob = candidate.get("redrob_signals") if isinstance(candidate.get("redrob_signals"), dict) else {}
    if _salary_invalid(redrob.get("expected_salary_range_inr_lpa")):
        issues.append("salary min greater than max")

    profile_years = parse_float(candidate.get("profile", {}).get("years_of_experience") if isinstance(candidate.get("profile"), dict) else None)
    career_months = features.career.total_career_months
    if profile_years is not None and career_months:
        delta_months = abs(profile_years * 12 - career_months)
        if delta_months > 48:
            issues.append(f"profile experience differs from career duration by {int(delta_months)} months")

    career_history = candidate.get("career_history")
    if isinstance(career_history, list):
        current_count = 0
        for index, role in enumerate(career_history):
            if not isinstance(role, dict):
                issues.append(f"career_history[{index}] is not an object")
                continue
            if not normalize_whitespace(role.get("description")):
                issues.append(f"career_history[{index}] has empty description")
            if role.get("is_current") is True:
                current_count += 1
                if role.get("end_date") is not None:
                    issues.append(f"current role {index} has end_date")
            if role.get("is_current") is False and role.get("end_date") is None:
                issues.append(f"non-current role {index} missing end_date")
        if current_count > 1:
            issues.append("multiple current roles")
        if career_history and current_count == 0:
            issues.append("no current role marked")

    education = candidate.get("education")
    if isinstance(education, list):
        for index, item in enumerate(education):
            if not isinstance(item, dict):
                continue
            start_year = parse_int(item.get("start_year"))
            end_year = parse_int(item.get("end_year"))
            if start_year is not None and end_year is not None and end_year < start_year:
                issues.append(f"education[{index}] end_year before start_year")

    if not issues:
        return []
    if len(issues) >= 4 or "candidate_id missing or malformed" in issues:
        severity = "high"
        penalty = TRAP_PENALTY_WEIGHTS["profile_data_inconsistency"]
    elif len(issues) >= 2:
        severity = "medium"
        penalty = TRAP_PENALTY_WEIGHTS["profile_data_inconsistency"] * 0.75
    else:
        severity = "medium"
        penalty = TRAP_PENALTY_WEIGHTS["profile_data_inconsistency"] * 0.55
    return [
        make_trap_signal(
            "profile_data_inconsistency",
            "Profile data inconsistency",
            severity,
            penalty,
            evidence=cap_list(issues, 6),
        )
    ]


def detect_platform_data_inconsistency(
    candidate: dict[str, Any],
    features: CandidateFeatures,
) -> list[TrapSignal]:
    signals = candidate.get("redrob_signals")
    signals = signals if isinstance(signals, dict) else {}
    issues: list[str] = []
    signup_date = parse_iso_date(signals.get("signup_date"))
    last_active = parse_iso_date(signals.get("last_active_date"))
    if signup_date and last_active and last_active < signup_date:
        issues.append("last_active_date earlier than signup_date")
    for field, low, high in [
        ("recruiter_response_rate", 0, 1),
        ("interview_completion_rate", 0, 1),
        ("offer_acceptance_rate", -1, 1),
        ("notice_period_days", 0, 180),
        ("github_activity_score", -1, 100),
    ]:
        value = parse_float(signals.get(field))
        if value is not None and not low <= value <= high:
            issues.append(f"{field} outside {low}..{high}")
    if _salary_invalid(signals.get("expected_salary_range_inr_lpa")):
        issues.append("salary min greater than max")
    negative_fields = [
        "profile_views_received_30d",
        "applications_submitted_30d",
        "connection_count",
        "endorsements_received",
        "search_appearance_30d",
        "saved_by_recruiters_30d",
    ]
    for field in negative_fields:
        value = parse_float(signals.get(field))
        if value is not None and value < 0:
            issues.append(f"{field} is negative")

    if not issues:
        return []
    severity = "high" if len(issues) >= 3 else "medium"
    return [
        make_trap_signal(
            "platform_data_inconsistency",
            "Platform data inconsistency",
            severity,
            TRAP_PENALTY_WEIGHTS["platform_data_inconsistency"] * (1.0 if severity == "high" else 0.75),
            evidence=cap_list(issues, 6),
        )
    ]


def detect_severe_low_availability(
    candidate: dict[str, Any],
    features: CandidateFeatures,
) -> list[TrapSignal]:
    signals = candidate.get("redrob_signals")
    signals = signals if isinstance(signals, dict) else {}
    flags = compute_redrob_risk_flags(signals)
    severe_names = [
        "inactive_180d",
        "low_recruiter_response_rate",
        "very_slow_response",
        "very_high_notice_period",
        "not_open_to_work",
    ]
    severe_flags = [name for name in severe_names if flags.get(name)]
    response_rate = parse_float(signals.get("recruiter_response_rate"))
    notice = parse_float(signals.get("notice_period_days"))
    if flags.get("inactive_180d") and response_rate is not None and response_rate < 0.10 and notice is not None and notice >= 120:
        return [
            make_trap_signal(
                "severe_low_availability",
                "Severe low availability",
                "high",
                TRAP_PENALTY_WEIGHTS["severe_low_availability"],
                evidence=severe_flags,
                notes="Extreme availability risk is handled here; normal behavior scoring happens in Section 6.",
            )
        ]
    if len(severe_flags) >= 3:
        return [
            make_trap_signal(
                "severe_low_availability",
                "Multiple severe availability risks",
                "medium",
                TRAP_PENALTY_WEIGHTS["severe_low_availability"] * 0.75,
                evidence=severe_flags,
            )
        ]
    return []


def detect_honeypot_like_profile_shape(
    candidate: dict[str, Any],
    features: CandidateFeatures,
    prior_signals: list[TrapSignal] | None = None,
) -> list[TrapSignal]:
    prior_signals = prior_signals or []
    families = {signal.code for signal in prior_signals}
    suspicious_families: list[str] = []
    if "wrong_role_keyword_stuffing" in families:
        suspicious_families.append("wrong-role AI keyword stuffing")
    if "expert_skill_zero_duration" in families:
        suspicious_families.append("expert skill duration inconsistency")
    if "profile_data_inconsistency" in families:
        suspicious_families.append("profile inconsistency")
    if "platform_data_inconsistency" in families:
        suspicious_families.append("platform inconsistency")
    if "weak_ai_hype_without_production" in families:
        suspicious_families.append("weak AI hype without production")
    if features.diagnostic_flags.wrong_role_title and _ai_skill_hits(features):
        suspicious_families.append("many AI skills with wrong title")
    if not features.diagnostic_flags.has_production_evidence:
        suspicious_families.append("no production evidence")
    if not features.diagnostic_flags.has_real_retrieval_or_ranking_evidence:
        suspicious_families.append("no career retrieval/ranking evidence")

    unique_families = []
    for family in suspicious_families:
        if family not in unique_families:
            unique_families.append(family)
    if len(unique_families) < 3:
        return []

    severity = "critical" if len(unique_families) >= 4 else "high"
    penalty = 0.16 if severity == "critical" else 0.11
    return [
        make_trap_signal(
            "honeypot_like_profile_shape",
            "Honeypot-like profile shape",
            severity,
            penalty,
            evidence=cap_list(unique_families, 6),
            notes="This is not a confirmed hidden honeypot label.",
        )
    ]


def collect_trap_signals(
    candidate: dict[str, Any],
    features: CandidateFeatures | None = None,
) -> list[TrapSignal]:
    active_features = features or extract_candidate_features(candidate)
    signals: list[TrapSignal] = []
    detectors = [
        detect_wrong_role_keyword_stuffing,
        detect_weak_ai_hype_without_production,
        detect_consulting_only_no_product,
        detect_non_target_ai_only,
        detect_expert_skill_zero_duration,
        detect_profile_data_inconsistency,
        detect_platform_data_inconsistency,
        detect_severe_low_availability,
    ]
    for detector in detectors:
        signals.extend(detector(candidate, active_features))
    signals.extend(detect_honeypot_like_profile_shape(candidate, active_features, signals))
    return signals


def compute_trap_penalty_scorecard(
    candidate: dict[str, Any],
    features: CandidateFeatures | None = None,
) -> TrapPenaltyScorecard:
    active_features = features or extract_candidate_features(candidate)
    signals = collect_trap_signals(candidate, active_features)
    total = clamp_penalty(sum(signal.penalty for signal in signals))
    severity_band = get_trap_severity_band(total)
    risk_flags = {
        "wrong_role_keyword_stuffing": any(signal.code == "wrong_role_keyword_stuffing" for signal in signals),
        "weak_ai_hype_without_production": any(signal.code == "weak_ai_hype_without_production" for signal in signals),
        "consulting_only_no_product": any(signal.code == "consulting_only_no_product" for signal in signals),
        "non_target_ai_only": any(signal.code == "non_target_ai_only" for signal in signals),
        "expert_skill_zero_duration": any(signal.code == "expert_skill_zero_duration" for signal in signals),
        "profile_data_inconsistency": any(signal.code == "profile_data_inconsistency" for signal in signals),
        "platform_data_inconsistency": any(signal.code == "platform_data_inconsistency" for signal in signals),
        "severe_low_availability": any(signal.code == "severe_low_availability" for signal in signals),
        "honeypot_like_profile_shape": any(signal.code == "honeypot_like_profile_shape" for signal in signals),
    }
    return TrapPenaltyScorecard(
        candidate_id=str(candidate.get("candidate_id", "")),
        total_penalty=round_score(total, 6),
        severity_band=severity_band,
        penalty_multiplier=get_trap_penalty_multiplier(total),
        signals=signals,
        risk_flags=risk_flags,
        short_summary=_short_summary(severity_band, signals),
    )


def trap_scorecard_to_flat_dict(scorecard: TrapPenaltyScorecard) -> dict[str, Any]:
    row: dict[str, Any] = {
        "candidate_id": scorecard.candidate_id,
        "total_penalty": scorecard.total_penalty,
        "severity_band": scorecard.severity_band,
        "penalty_multiplier": scorecard.penalty_multiplier,
        "signal_count": len(scorecard.signals),
        "signal_codes": safe_join([signal.code for signal in scorecard.signals]),
        "short_summary": scorecard.short_summary,
    }
    row.update(scorecard.risk_flags)
    return row


def apply_trap_penalty_preview(score_before_penalty: float, scorecard: TrapPenaltyScorecard) -> float:
    if not isinstance(score_before_penalty, (int, float)) or isinstance(score_before_penalty, bool):
        return 0.0
    return round_score(max(0.0, min(1.0, float(score_before_penalty) * scorecard.penalty_multiplier)), 6)


def _ai_skill_hits(features: CandidateFeatures) -> list[str]:
    hits = (
        features.skills.retrieval_ranking_skill_hits
        + features.skills.embedding_vector_skill_hits
        + features.skills.evaluation_skill_hits
        + features.skills.weak_ai_hype_skill_hits
        + features.skills.non_target_ai_skill_hits
    )
    unique_hits: list[str] = []
    for hit in hits:
        if hit not in unique_hits:
            unique_hits.append(hit)
    return unique_hits


def _salary_invalid(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    minimum = parse_float(value.get("min"))
    maximum = parse_float(value.get("max"))
    return minimum is not None and maximum is not None and minimum > maximum


def _short_summary(severity_band: str, signals: list[TrapSignal]) -> str:
    if not signals:
        return "Clean profile: no major trap signals detected."
    codes = [signal.code.replace("_", " ") for signal in signals[:3]]
    if severity_band in {"high_risk", "extreme_risk"}:
        return f"{severity_band.replace('_', ' ').title()}: {safe_join(codes)}."
    return f"{severity_band.replace('_', ' ').title()}: {safe_join(codes)}."
