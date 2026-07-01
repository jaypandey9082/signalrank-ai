from __future__ import annotations

from typing import Any


FEATURE_WEIGHTS_DRAFT = {
    "career_evidence": 0.22,
    "retrieval_ranking": 0.18,
    "skills": 0.13,
    "experience_fit": 0.10,
    "product_company": 0.10,
    "redrob_availability": 0.10,
    "location_logistics": 0.07,
    "evaluation_experience": 0.05,
    "education_signal": 0.03,
    "verification_github": 0.02,
}

PENALTY_WEIGHTS_DRAFT = {
    "wrong_role_keyword_stuffing": 0.25,
    "consulting_only_no_product": 0.12,
    "inactive_candidate": 0.12,
    "low_recruiter_response": 0.08,
    "high_notice_period": 0.07,
    "invalid_salary_range": 0.08,
    "platform_date_inconsistency": 0.15,
    "expert_skill_zero_duration": 0.08,
    "weak_ai_hype_without_production": 0.10,
    "non_target_ai_only": 0.08,
}

STATIC_FIT_WEIGHTS = {
    "career_evidence": 0.26,
    "retrieval_ranking": 0.21,
    "skills": 0.15,
    "experience_fit": 0.12,
    "product_company": 0.10,
    "location_fit": 0.07,
    "evaluation_experience": 0.06,
    "education_signal": 0.03,
}

REDROB_COMPONENT_WEIGHTS = {
    "activity_recency": 0.20,
    "availability_intent": 0.16,
    "recruiter_responsiveness": 0.20,
    "notice_logistics": 0.12,
    "market_interest": 0.10,
    "process_reliability": 0.12,
    "profile_trust": 0.07,
    "technical_activity": 0.03,
}

TRAP_PENALTY_WEIGHTS = {
    "wrong_role_keyword_stuffing": 0.24,
    "weak_ai_hype_without_production": 0.14,
    "consulting_only_no_product": 0.12,
    "non_target_ai_only": 0.10,
    "expert_skill_zero_duration": 0.10,
    "profile_data_inconsistency": 0.12,
    "platform_data_inconsistency": 0.10,
    "severe_low_availability": 0.08,
}

TRAP_PENALTY_CAP = 0.65

TRAP_SEVERITY_BANDS = [
    {"label": "clean", "min": 0.00, "max": 0.049, "multiplier": 1.00},
    {"label": "minor_risk", "min": 0.05, "max": 0.149, "multiplier": 0.97},
    {"label": "moderate_risk", "min": 0.15, "max": 0.299, "multiplier": 0.90},
    {"label": "high_risk", "min": 0.30, "max": 0.499, "multiplier": 0.75},
    {"label": "extreme_risk", "min": 0.50, "max": 1.00, "multiplier": 0.50},
]

COMBINED_SCORE_FORMULA = (
    "combined_score = static_fit_score * behavior_multiplier * trap_penalty_multiplier, "
    "then guardrail caps are applied"
)

GUARDRAIL_CAPS = {
    "extreme_trap_risk": 0.25,
    "high_trap_risk": 0.45,
    "wrong_role_keyword_stuffing": 0.30,
    "weak_ai_hype_without_production": 0.42,
    "no_real_retrieval_or_ranking_evidence": 0.58,
    "consulting_only_no_product": 0.60,
    "non_target_ai_only": 0.50,
    "very_low_hireability": 0.62,
    "low_hireability": 0.70,
}

FINAL_SCORE_BANDS = [
    {"label": "elite_fit", "min": 0.82, "max": 1.00},
    {"label": "strong_fit", "min": 0.70, "max": 0.819},
    {"label": "good_fit", "min": 0.58, "max": 0.699},
    {"label": "borderline_fit", "min": 0.42, "max": 0.579},
    {"label": "weak_fit", "min": 0.00, "max": 0.419},
]

RANKING_DEFAULT_TOP_K = 100

RANKING_QUALITY_THRESHOLDS = {
    "top10_min_real_retrieval_evidence": 7,
    "top10_max_wrong_role_titles": 0,
    "top100_max_high_or_extreme_trap_rate": 0.10,
    "top100_max_keyword_stuffing_rate": 0.10,
}

DEFAULT_AS_OF_DATE = "2026-07-01"

BEHAVIOR_MULTIPLIER_BANDS = [
    {"label": "excellent_hireability", "min": 0.85, "max": 1.00, "multiplier": 1.08},
    {"label": "good_hireability", "min": 0.70, "max": 0.849, "multiplier": 1.04},
    {"label": "neutral_hireability", "min": 0.55, "max": 0.699, "multiplier": 1.00},
    {"label": "risky_hireability", "min": 0.40, "max": 0.549, "multiplier": 0.93},
    {"label": "low_hireability", "min": 0.25, "max": 0.399, "multiplier": 0.85},
    {"label": "very_low_hireability", "min": 0.00, "max": 0.249, "multiplier": 0.78},
]

STATIC_SCORE_BANDS = [
    {"label": "strong_static_fit", "min": 0.80, "max": 1.00},
    {"label": "good_static_fit", "min": 0.65, "max": 0.799},
    {"label": "adjacent_static_fit", "min": 0.45, "max": 0.649},
    {"label": "weak_static_fit", "min": 0.00, "max": 0.449},
]

EXPERIENCE_BANDS = [
    {"label": "too_junior", "min": 0, "max": 3.99, "score": 0.20},
    {"label": "slightly_junior", "min": 4.0, "max": 4.99, "score": 0.55},
    {"label": "good", "min": 5.0, "max": 5.99, "score": 0.85},
    {"label": "ideal", "min": 6.0, "max": 8.0, "score": 1.00},
    {"label": "good_senior", "min": 8.01, "max": 9.0, "score": 0.85},
    {"label": "slightly_senior", "min": 9.01, "max": 10.5, "score": 0.55},
    {"label": "too_senior", "min": 10.51, "max": 50, "score": 0.35},
]

UNKNOWN_EXPERIENCE_BAND = {"label": "unknown", "min": None, "max": None, "score": 0.0}


def validate_feature_weights(weights: dict[str, float] | None = None) -> bool:
    active_weights = weights or FEATURE_WEIGHTS_DRAFT
    return abs(sum(active_weights.values()) - 1.0) <= 0.001


def validate_static_fit_weights(weights: dict[str, float] | None = None) -> bool:
    active_weights = weights or STATIC_FIT_WEIGHTS
    return abs(sum(active_weights.values()) - 1.0) <= 0.001


def validate_redrob_weights(weights: dict[str, float] | None = None) -> bool:
    active_weights = weights or REDROB_COMPONENT_WEIGHTS
    return abs(sum(active_weights.values()) - 1.0) <= 0.001


def get_experience_band(years: float | int | None) -> dict[str, Any]:
    if not isinstance(years, (int, float)) or isinstance(years, bool):
        return UNKNOWN_EXPERIENCE_BAND.copy()

    for band in EXPERIENCE_BANDS:
        if band["min"] <= float(years) <= band["max"]:
            return band.copy()
    return UNKNOWN_EXPERIENCE_BAND.copy()


def get_static_score_band(score: float | int | None) -> str:
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return "unknown"
    score_float = float(score)
    for band in STATIC_SCORE_BANDS:
        if band["min"] - 0.001 <= score_float <= band["max"] + 0.001:
            return band["label"]
    return "unknown"


def get_behavior_band(score: float | int | None) -> str:
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return "unknown"
    score_float = float(score)
    for band in BEHAVIOR_MULTIPLIER_BANDS:
        if band["min"] - 0.001 <= score_float <= band["max"] + 0.001:
            return band["label"]
    return "unknown"


def get_behavior_multiplier(score: float | int | None) -> float:
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return 0.78
    score_float = float(score)
    for band in BEHAVIOR_MULTIPLIER_BANDS:
        if band["min"] - 0.001 <= score_float <= band["max"] + 0.001:
            return float(band["multiplier"])
    return 0.78


def get_trap_severity_band(penalty: float | int | None) -> str:
    if not isinstance(penalty, (int, float)) or isinstance(penalty, bool):
        return "unknown"
    penalty_float = float(penalty)
    for band in TRAP_SEVERITY_BANDS:
        if band["min"] - 0.001 <= penalty_float <= band["max"] + 0.001:
            return band["label"]
    return "unknown"


def get_trap_penalty_multiplier(penalty: float | int | None) -> float:
    if not isinstance(penalty, (int, float)) or isinstance(penalty, bool):
        return 0.50
    penalty_float = float(penalty)
    for band in TRAP_SEVERITY_BANDS:
        if band["min"] - 0.001 <= penalty_float <= band["max"] + 0.001:
            return float(band["multiplier"])
    return 0.50


def get_final_score_band(score: float | int | None) -> str:
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return "unknown"
    score_float = float(score)
    for band in FINAL_SCORE_BANDS:
        if band["min"] - 0.001 <= score_float <= band["max"] + 0.001:
            return band["label"]
    return "unknown"


def combined_scoring_config_to_markdown() -> str:
    lines = [
        "## Section 8 Combined Ranking Preview",
        "",
        f"Formula: `{COMBINED_SCORE_FORMULA}`.",
        "",
        "### Guardrail Caps",
        "",
    ]
    lines.extend(f"- {name}: {cap:.2f}" for name, cap in GUARDRAIL_CAPS.items())
    lines.extend(["", "### Final Score Bands", ""])
    for band in FINAL_SCORE_BANDS:
        lines.append(f"- {band['label']}: {band['min']} to {band['max']}")
    lines.extend(["", "### Ranking Quality Thresholds", ""])
    for name, value in RANKING_QUALITY_THRESHOLDS.items():
        lines.append(f"- {name}: {value}")
    return "\n".join(lines) + "\n"


def scoring_config_to_markdown() -> str:
    lines = [
        "# Draft Scoring Configuration",
        "",
        "## Section 5 Static Fit Weights",
        "",
        "These weights are for static candidate-job fit only. They are not final ranking weights.",
        "",
    ]
    lines.extend(f"- {name}: {weight:.2f}" for name, weight in STATIC_FIT_WEIGHTS.items())
    lines.extend(["", "## Static Score Bands", ""])
    for band in STATIC_SCORE_BANDS:
        lines.append(f"- {band['label']}: {band['min']} to {band['max']}")
    lines.extend(
        [
            "",
            "## Section 6 Redrob Behavior Weights",
            "",
            "These weights score hireability/readiness only. They do not replace static job fit.",
            "",
        ]
    )
    lines.extend(f"- {name}: {weight:.2f}" for name, weight in REDROB_COMPONENT_WEIGHTS.items())
    lines.extend(["", "## Behavior Multiplier Bands", ""])
    for band in BEHAVIOR_MULTIPLIER_BANDS:
        lines.append(
            f"- {band['label']}: {band['min']} to {band['max']} -> {band['multiplier']:.2f}"
        )
    lines.extend(
        [
            "",
            "## Section 7 Trap Penalty Weights",
            "",
            "These additive penalties flag suspicious profile shapes. They are capped before use.",
            "",
        ]
    )
    lines.extend(f"- {name}: {weight:.2f}" for name, weight in TRAP_PENALTY_WEIGHTS.items())
    lines.extend(["", f"Trap penalty cap: {TRAP_PENALTY_CAP:.2f}", "", "## Trap Severity Bands", ""])
    for band in TRAP_SEVERITY_BANDS:
        lines.append(
            f"- {band['label']}: {band['min']} to {band['max']} -> {band['multiplier']:.2f}"
        )
    lines.extend(["", combined_scoring_config_to_markdown().rstrip()])
    lines.extend(
        [
            "",
            "## Earlier Draft Feature Weights",
            "",
            "These are retained from Section 3 as planning notes.",
            "",
        ]
    )
    lines.extend(f"- {name}: {weight:.2f}" for name, weight in FEATURE_WEIGHTS_DRAFT.items())
    lines.extend(["", "## Draft Penalty Weights", "", "These are not applied in Section 5.", ""])
    lines.extend(f"- {name}: {weight:.2f}" for name, weight in PENALTY_WEIGHTS_DRAFT.items())
    lines.extend(["", "## Experience Bands", ""])
    for band in EXPERIENCE_BANDS:
        lines.append(
            f"- {band['label']}: {band['min']} to {band['max']} years -> {band['score']:.2f}"
        )
    return "\n".join(lines) + "\n"
