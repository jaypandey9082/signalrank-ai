from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.features import CandidateFeatures, extract_candidate_features
from src.redrob_scoring import RedrobScorecard, compute_redrob_scorecard
from src.scoring import StaticScorecard, compute_static_scorecard
from src.scoring_config import GUARDRAIL_CAPS, get_final_score_band
from src.trap_penalties import TrapPenaltyScorecard, compute_trap_penalty_scorecard
from src.utils import cap_list, round_score, safe_join


@dataclass
class GuardrailCap:
    code: str
    cap: float
    applied: bool
    evidence: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CombinedScorecard:
    candidate_id: str
    static_fit_score: float
    redrob_availability_score: float
    behavior_multiplier: float
    trap_total_penalty: float
    trap_penalty_multiplier: float
    score_before_caps: float
    score_after_caps: float
    final_score: float
    final_score_band: str
    applied_caps: list[GuardrailCap]
    static_band: str
    behavior_band: str
    trap_severity_band: str
    title: str
    title_category: str
    years_of_experience: float | None
    location: str
    location_category: str
    key_flags: dict[str, bool]
    evidence_seeds: list[str]
    debug_summary: str


def clamp01(value: float | int | None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def make_guardrail_cap(
    code: str,
    cap: float,
    applied: bool,
    evidence: list[str] | None = None,
    notes: str = "",
) -> GuardrailCap:
    return GuardrailCap(
        code=code,
        cap=round_score(clamp01(cap), 6),
        applied=applied,
        evidence=evidence or [],
        notes=notes,
    )


def apply_caps(score: float, caps: list[GuardrailCap]) -> tuple[float, list[GuardrailCap]]:
    applied_caps = [cap for cap in caps if cap.applied]
    if not applied_caps:
        return round_score(clamp01(score), 6), []
    lowest_cap = min(cap.cap for cap in applied_caps)
    return round_score(min(clamp01(score), lowest_cap), 6), applied_caps


def determine_guardrail_caps(
    candidate: dict,
    features: CandidateFeatures,
    static_scorecard: StaticScorecard,
    redrob_scorecard: RedrobScorecard,
    trap_scorecard: TrapPenaltyScorecard,
) -> list[GuardrailCap]:
    flags = features.diagnostic_flags
    trap_flags = trap_scorecard.risk_flags
    caps: list[GuardrailCap] = []

    caps.append(
        make_guardrail_cap(
            "extreme_trap_risk",
            GUARDRAIL_CAPS["extreme_trap_risk"],
            trap_scorecard.severity_band == "extreme_risk",
            evidence=[f"trap_severity_band={trap_scorecard.severity_band}"],
            notes="Extreme trap risk cannot occupy top preview ranks.",
        )
    )
    caps.append(
        make_guardrail_cap(
            "high_trap_risk",
            GUARDRAIL_CAPS["high_trap_risk"],
            trap_scorecard.severity_band == "high_risk",
            evidence=[f"trap_severity_band={trap_scorecard.severity_band}"],
            notes="High trap risk is capped for ranking safety.",
        )
    )
    caps.append(
        make_guardrail_cap(
            "wrong_role_keyword_stuffing",
            GUARDRAIL_CAPS["wrong_role_keyword_stuffing"],
            trap_flags.get("wrong_role_keyword_stuffing", False),
            evidence=[f"title={features.profile.current_title}", "wrong_role_keyword_stuffing=True"],
        )
    )
    caps.append(
        make_guardrail_cap(
            "weak_ai_hype_without_production",
            GUARDRAIL_CAPS["weak_ai_hype_without_production"],
            trap_flags.get("weak_ai_hype_without_production", False) and not flags.has_production_evidence,
            evidence=["weak AI hype without production evidence"],
        )
    )
    caps.append(
        make_guardrail_cap(
            "no_real_retrieval_or_ranking_evidence",
            GUARDRAIL_CAPS["no_real_retrieval_or_ranking_evidence"],
            not flags.has_real_retrieval_or_ranking_evidence
            and not flags.has_evaluation_evidence
            and not flags.has_production_evidence,
            evidence=[
                "no real retrieval/ranking evidence",
                "no evaluation evidence",
                "no production evidence",
            ],
            notes="Generic backend/data skill profiles should not drift into top preview ranks.",
        )
    )
    caps.append(
        make_guardrail_cap(
            "consulting_only_no_product",
            GUARDRAIL_CAPS["consulting_only_no_product"],
            trap_flags.get("consulting_only_no_product", False),
            evidence=["consulting/service-only profile without product retrieval evidence"],
        )
    )
    caps.append(
        make_guardrail_cap(
            "non_target_ai_only",
            GUARDRAIL_CAPS["non_target_ai_only"],
            trap_flags.get("non_target_ai_only", False),
            evidence=["non-target AI specialty without retrieval/evaluation evidence"],
        )
    )
    caps.append(
        make_guardrail_cap(
            "very_low_hireability",
            GUARDRAIL_CAPS["very_low_hireability"],
            redrob_scorecard.behavior_band == "very_low_hireability",
            evidence=[f"behavior_band={redrob_scorecard.behavior_band}"],
        )
    )
    caps.append(
        make_guardrail_cap(
            "low_hireability",
            GUARDRAIL_CAPS["low_hireability"],
            redrob_scorecard.behavior_band == "low_hireability",
            evidence=[f"behavior_band={redrob_scorecard.behavior_band}"],
        )
    )
    return caps


def collect_evidence_seeds(
    features: CandidateFeatures,
    static_scorecard: StaticScorecard,
    redrob_scorecard: RedrobScorecard,
    trap_scorecard: TrapPenaltyScorecard,
    max_items: int = 8,
) -> list[str]:
    seeds: list[str] = []
    _append_seed(seeds, f"title: {features.profile.current_title}")
    if features.profile.years_of_experience is not None:
        _append_seed(seeds, f"experience: {features.profile.years_of_experience} years")
    if features.profile.location:
        _append_seed(seeds, f"location: {features.profile.location}")
    for snippet in features.career.career_evidence_snippets:
        _append_seed(seeds, snippet)
    for component in static_scorecard.components:
        for item in component.evidence:
            _append_seed(seeds, item)
    _append_seed(seeds, redrob_scorecard.short_summary)
    if trap_scorecard.signals:
        _append_seed(seeds, trap_scorecard.short_summary)
    return cap_list(seeds, max_items)


def build_debug_summary(
    features: CandidateFeatures,
    static_scorecard: StaticScorecard,
    redrob_scorecard: RedrobScorecard,
    trap_scorecard: TrapPenaltyScorecard,
    final_score: float,
    applied_caps: list[GuardrailCap],
) -> str:
    parts: list[str] = []
    if features.diagnostic_flags.has_real_retrieval_or_ranking_evidence:
        parts.append("static fit includes retrieval/ranking evidence")
    elif features.diagnostic_flags.has_production_evidence:
        parts.append("static fit has production evidence but limited retrieval/ranking proof")
    else:
        parts.append("static fit has limited production retrieval evidence")

    parts.append(redrob_scorecard.behavior_band.replace("_", " "))
    if applied_caps:
        parts.append(f"capped by {safe_join([cap.code for cap in applied_caps])}")
    elif trap_scorecard.severity_band == "clean":
        parts.append("no major trap cap applied")
    else:
        parts.append(f"trap band {trap_scorecard.severity_band}")
    parts.append(f"preview score {final_score:.3f}")
    return "; ".join(parts) + "."


def compute_combined_scorecard(
    candidate: dict,
    include_evidence: bool = True,
    include_matched_signal_terms: bool = True,
) -> CombinedScorecard:
    features = extract_candidate_features(
        candidate,
        include_evidence=include_evidence,
        include_matched_signal_terms=include_matched_signal_terms,
    )
    static_scorecard = compute_static_scorecard(features)
    redrob_scorecard = compute_redrob_scorecard(candidate)
    trap_scorecard = compute_trap_penalty_scorecard(candidate, features)
    score_before_caps = round_score(
        clamp01(
            static_scorecard.static_fit_score
            * redrob_scorecard.behavior_multiplier
            * trap_scorecard.penalty_multiplier
        ),
        6,
    )
    caps = determine_guardrail_caps(
        candidate,
        features,
        static_scorecard,
        redrob_scorecard,
        trap_scorecard,
    )
    score_after_caps, applied_caps = apply_caps(score_before_caps, caps)
    final_score = round_score(clamp01(score_after_caps), 6)
    key_flags = {
        "has_real_retrieval_or_ranking_evidence": features.diagnostic_flags.has_real_retrieval_or_ranking_evidence,
        "has_evaluation_evidence": features.diagnostic_flags.has_evaluation_evidence,
        "has_production_evidence": features.diagnostic_flags.has_production_evidence,
        "wrong_role_title": features.diagnostic_flags.wrong_role_title,
        "keyword_stuffing_shape": features.diagnostic_flags.has_keyword_stuffing_shape,
        "consulting_only_career": features.career.consulting_only_career,
        "low_or_very_low_hireability": redrob_scorecard.behavior_band in {"low_hireability", "very_low_hireability"},
        "high_or_extreme_trap_risk": trap_scorecard.severity_band in {"high_risk", "extreme_risk"},
    }
    evidence_seeds = collect_evidence_seeds(
        features,
        static_scorecard,
        redrob_scorecard,
        trap_scorecard,
    )
    debug_summary = build_debug_summary(
        features,
        static_scorecard,
        redrob_scorecard,
        trap_scorecard,
        final_score,
        applied_caps,
    )
    return CombinedScorecard(
        candidate_id=features.candidate_id,
        static_fit_score=static_scorecard.static_fit_score,
        redrob_availability_score=redrob_scorecard.redrob_availability_score,
        behavior_multiplier=redrob_scorecard.behavior_multiplier,
        trap_total_penalty=trap_scorecard.total_penalty,
        trap_penalty_multiplier=trap_scorecard.penalty_multiplier,
        score_before_caps=score_before_caps,
        score_after_caps=score_after_caps,
        final_score=final_score,
        final_score_band=get_final_score_band(final_score),
        applied_caps=applied_caps,
        static_band=static_scorecard.score_band,
        behavior_band=redrob_scorecard.behavior_band,
        trap_severity_band=trap_scorecard.severity_band,
        title=features.profile.current_title,
        title_category=features.profile.title_category,
        years_of_experience=features.profile.years_of_experience,
        location=features.profile.location,
        location_category=features.profile.location_category,
        key_flags=key_flags,
        evidence_seeds=evidence_seeds,
        debug_summary=debug_summary,
    )


def combined_scorecard_to_flat_dict(scorecard: CombinedScorecard) -> dict[str, Any]:
    row: dict[str, Any] = {
        "candidate_id": scorecard.candidate_id,
        "final_score_preview": scorecard.final_score,
        "final_score_band": scorecard.final_score_band,
        "static_fit_score": scorecard.static_fit_score,
        "redrob_availability_score": scorecard.redrob_availability_score,
        "behavior_multiplier": scorecard.behavior_multiplier,
        "trap_total_penalty": scorecard.trap_total_penalty,
        "trap_penalty_multiplier": scorecard.trap_penalty_multiplier,
        "score_before_caps": scorecard.score_before_caps,
        "score_after_caps": scorecard.score_after_caps,
        "applied_cap_codes": safe_join([cap.code for cap in scorecard.applied_caps]),
        "static_band": scorecard.static_band,
        "behavior_band": scorecard.behavior_band,
        "trap_severity_band": scorecard.trap_severity_band,
        "title": scorecard.title,
        "title_category": scorecard.title_category,
        "years_of_experience": scorecard.years_of_experience,
        "location": scorecard.location,
        "location_category": scorecard.location_category,
        "debug_summary": scorecard.debug_summary,
    }
    row.update(scorecard.key_flags)
    for index, seed in enumerate(scorecard.evidence_seeds[:5], start=1):
        row[f"evidence_seed_{index}"] = seed
    return row


def _append_seed(seeds: list[str], value: object) -> None:
    seed = " ".join(str(value or "").split())
    if seed and seed not in seeds:
        seeds.append(seed[:220])
