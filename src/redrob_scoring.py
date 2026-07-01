from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean
from typing import Any

from src.scoring_config import (
    DEFAULT_AS_OF_DATE,
    REDROB_COMPONENT_WEIGHTS,
    get_behavior_band,
    get_behavior_multiplier,
)
from src.utils import round_score


DEFAULT_AS_OF_DATE_PARSED = date.fromisoformat(DEFAULT_AS_OF_DATE)


@dataclass
class RedrobComponentScore:
    name: str
    raw_score: float
    weight: float
    weighted_score: float
    evidence: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class RedrobScorecard:
    candidate_id: str
    redrob_availability_score: float
    behavior_band: str
    behavior_multiplier: float
    components: list[RedrobComponentScore]
    risk_flags: dict[str, bool]
    raw_snapshot: dict[str, object]
    short_summary: str


def parse_iso_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def days_since(date_value: object, as_of_date: str | date | None = None) -> int | None:
    parsed_date = parse_iso_date(date_value)
    reference = _as_of_date(as_of_date)
    if parsed_date is None or reference is None:
        return None
    return max((reference - parsed_date).days, 0)


def clamp01(value: float | int | None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def saturating_score(value: float | int | None, good_at: float) -> float:
    if good_at <= 0 or not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        return 0.0
    return min(float(value) / good_at, 1.0)


def make_redrob_component(
    name: str,
    raw_score: float,
    weight: float,
    evidence: list[str] | None = None,
    notes: str = "",
) -> RedrobComponentScore:
    raw = round_score(clamp01(raw_score), 6)
    weight_value = round_score(weight, 6)
    return RedrobComponentScore(
        name=name,
        raw_score=raw,
        weight=weight_value,
        weighted_score=round_score(raw * weight_value, 6),
        evidence=evidence or [],
        notes=notes,
    )


def score_activity_recency(
    signals: dict[str, Any],
    as_of_date: str | date | None = None,
) -> RedrobComponentScore:
    last_active = signals.get("last_active_date")
    days = days_since(last_active, as_of_date)
    if days is None:
        raw = 0.20
        evidence = ["last_active_date missing or invalid"]
    elif days <= 7:
        raw = 1.00
        evidence = [f"last_active_date={last_active}, {days} days before reference date"]
    elif days <= 30:
        raw = 0.90
        evidence = [f"last_active_date={last_active}, {days} days before reference date"]
    elif days <= 60:
        raw = 0.75
        evidence = [f"last_active_date={last_active}, {days} days before reference date"]
    elif days <= 90:
        raw = 0.55
        evidence = [f"last_active_date={last_active}, {days} days before reference date"]
    elif days <= 180:
        raw = 0.30
        evidence = [f"last_active_date={last_active}, {days} days before reference date"]
    else:
        raw = 0.10
        evidence = [f"last_active_date={last_active}, inactive for more than 180 days"]
    return make_redrob_component(
        "activity_recency",
        raw,
        REDROB_COMPONENT_WEIGHTS["activity_recency"],
        evidence=evidence,
        notes="Recent platform activity improves reachability.",
    )


def score_availability_intent(signals: dict[str, Any]) -> RedrobComponentScore:
    open_to_work = signals.get("open_to_work_flag") is True
    applications = _number_or_none(signals.get("applications_submitted_30d"))
    work_mode = str(signals.get("preferred_work_mode") or "").lower()
    willing = signals.get("willing_to_relocate") is True
    application_score = saturating_score(applications, 8)
    work_mode_score = {
        "flexible": 0.90,
        "hybrid": 0.85,
        "onsite": 0.80,
        "remote": 0.55 if not willing else 0.70,
    }.get(work_mode, 0.50)
    raw = 0.50 * (1.0 if open_to_work else 0.25) + 0.20 * application_score + 0.20 * work_mode_score
    raw += 0.10 if willing else 0.0
    return make_redrob_component(
        "availability_intent",
        raw,
        REDROB_COMPONENT_WEIGHTS["availability_intent"],
        evidence=[
            f"open_to_work={open_to_work}",
            f"applications_30d={applications}",
            f"preferred_work_mode={work_mode or '<missing>'}",
            f"willing_to_relocate={willing}",
        ],
        notes="Intent signals help but cannot replace role fit.",
    )


def score_recruiter_responsiveness(signals: dict[str, Any]) -> RedrobComponentScore:
    response_rate = _number_or_none(signals.get("recruiter_response_rate"))
    response_hours = _number_or_none(signals.get("avg_response_time_hours"))
    if response_rate is None:
        response_rate_score = 0.25
    elif response_rate >= 0.85:
        response_rate_score = 1.00
    elif response_rate >= 0.70:
        response_rate_score = 0.85
    elif response_rate >= 0.50:
        response_rate_score = 0.65
    elif response_rate >= 0.30:
        response_rate_score = 0.40
    else:
        response_rate_score = 0.15

    if response_hours is None:
        response_time_score = 0.35
    elif response_hours <= 24:
        response_time_score = 1.00
    elif response_hours <= 72:
        response_time_score = 0.75
    elif response_hours <= 168:
        response_time_score = 0.40
    else:
        response_time_score = 0.15

    raw = 0.70 * response_rate_score + 0.30 * response_time_score
    return make_redrob_component(
        "recruiter_responsiveness",
        raw,
        REDROB_COMPONENT_WEIGHTS["recruiter_responsiveness"],
        evidence=[
            f"recruiter_response_rate={response_rate}",
            f"avg_response_time_hours={response_hours}",
        ],
        notes="Response rate matters more than response speed.",
    )


def score_notice_logistics(signals: dict[str, Any]) -> RedrobComponentScore:
    notice = _number_or_none(signals.get("notice_period_days"))
    willing = signals.get("willing_to_relocate") is True
    work_mode = str(signals.get("preferred_work_mode") or "").lower()
    if notice is None:
        raw = 0.35
    elif notice <= 15:
        raw = 1.00
    elif notice <= 30:
        raw = 0.90
    elif notice <= 60:
        raw = 0.65
    elif notice <= 90:
        raw = 0.40
    elif notice <= 120:
        raw = 0.25
    else:
        raw = 0.15
    raw += 0.06 if willing else 0.0
    raw += 0.04 if work_mode in {"flexible", "hybrid"} else 0.0
    return make_redrob_component(
        "notice_logistics",
        raw,
        REDROB_COMPONENT_WEIGHTS["notice_logistics"],
        evidence=[f"notice_period_days={notice}", f"willing_to_relocate={willing}", f"work_mode={work_mode}"],
        notes="Long notice is a hiring-risk signal, not a rejection by itself.",
    )


def score_market_interest(signals: dict[str, Any]) -> RedrobComponentScore:
    views = _number_or_none(signals.get("profile_views_received_30d"))
    searches = _number_or_none(signals.get("search_appearance_30d"))
    saves = _number_or_none(signals.get("saved_by_recruiters_30d"))
    raw = (
        0.25 * saturating_score(views, 100)
        + 0.35 * saturating_score(searches, 300)
        + 0.40 * saturating_score(saves, 20)
    )
    return make_redrob_component(
        "market_interest",
        raw,
        REDROB_COMPONENT_WEIGHTS["market_interest"],
        evidence=[f"profile_views_30d={views}", f"search_appearance_30d={searches}", f"saved_by_recruiters_30d={saves}"],
        notes="Recruiter saves are treated as the strongest market-interest signal.",
    )


def score_process_reliability(signals: dict[str, Any]) -> RedrobComponentScore:
    interview = _number_or_none(signals.get("interview_completion_rate"))
    offer = _number_or_none(signals.get("offer_acceptance_rate"))
    interview_score = clamp01(interview)
    offer_score = 0.50 if offer == -1 or offer is None else clamp01(offer)
    raw = 0.70 * interview_score + 0.30 * offer_score
    return make_redrob_component(
        "process_reliability",
        raw,
        REDROB_COMPONENT_WEIGHTS["process_reliability"],
        evidence=[f"interview_completion_rate={interview}", f"offer_acceptance_rate={offer}"],
        notes="No offer history is treated as neutral, not bad.",
    )


def score_profile_trust(signals: dict[str, Any]) -> RedrobComponentScore:
    completeness = clamp01(_number_or_none(signals.get("profile_completeness_score")) / 100 if _number_or_none(signals.get("profile_completeness_score")) is not None else None)
    verification_values = [
        signals.get("verified_email") is True,
        signals.get("verified_phone") is True,
        signals.get("linkedin_connected") is True,
    ]
    verification_score = sum(1 for value in verification_values if value) / 3
    assessment_scores = _assessment_values(signals)
    assessment_presence = 1.0 if assessment_scores else 0.0
    connection_score = saturating_score(_number_or_none(signals.get("connection_count")), 500)
    endorsement_score = saturating_score(_number_or_none(signals.get("endorsements_received")), 100)
    raw = (
        0.40 * completeness
        + 0.30 * verification_score
        + 0.15 * assessment_presence
        + 0.10 * connection_score
        + 0.05 * endorsement_score
    )
    return make_redrob_component(
        "profile_trust",
        raw,
        REDROB_COMPONENT_WEIGHTS["profile_trust"],
        evidence=[
            f"profile_completeness_score={signals.get('profile_completeness_score')}",
            f"verification_count={sum(1 for value in verification_values if value)}",
            f"assessment_count={len(assessment_scores)}",
        ],
        notes="Profile trust combines completeness, verification, and lightweight social proof.",
    )


def score_technical_activity(signals: dict[str, Any]) -> RedrobComponentScore:
    github = _number_or_none(signals.get("github_activity_score"))
    if github is None:
        github_score = 0.25
    elif github == -1:
        github_score = 0.35
    else:
        github_score = clamp01(github / 100)
    assessment_scores = _assessment_values(signals)
    avg_assessment = mean(assessment_scores) / 100 if assessment_scores else 0.25
    raw = 0.65 * github_score + 0.35 * clamp01(avg_assessment)
    return make_redrob_component(
        "technical_activity",
        raw,
        REDROB_COMPONENT_WEIGHTS["technical_activity"],
        evidence=[f"github_activity_score={github}", f"assessment_count={len(assessment_scores)}"],
        notes="Missing GitHub is neutral-low, not zero.",
    )


def compute_redrob_risk_flags(
    signals: dict[str, Any],
    as_of_date: str | date | None = None,
) -> dict[str, bool]:
    inactive_days = days_since(signals.get("last_active_date"), as_of_date)
    response_rate = _number_or_none(signals.get("recruiter_response_rate"))
    response_hours = _number_or_none(signals.get("avg_response_time_hours"))
    notice = _number_or_none(signals.get("notice_period_days"))
    signup_date = parse_iso_date(signals.get("signup_date"))
    last_active = parse_iso_date(signals.get("last_active_date"))
    return {
        "inactive_180d": inactive_days is not None and inactive_days > 180,
        "inactive_90d": inactive_days is not None and inactive_days > 90,
        "not_open_to_work": signals.get("open_to_work_flag") is not True,
        "low_recruiter_response_rate": response_rate is not None and response_rate < 0.20,
        "very_slow_response": response_hours is not None and response_hours > 168,
        "high_notice_period": notice is not None and notice >= 90,
        "very_high_notice_period": notice is not None and notice >= 120,
        "not_willing_to_relocate": signals.get("willing_to_relocate") is not True,
        "low_interview_completion": _number_or_none(signals.get("interview_completion_rate")) is not None
        and _number_or_none(signals.get("interview_completion_rate")) < 0.50,
        "unverified_profile": not any(
            signals.get(field) is True for field in ("verified_email", "verified_phone", "linkedin_connected")
        ),
        "platform_dates_invalid": signup_date is not None and last_active is not None and last_active < signup_date,
        "salary_range_invalid": _salary_range_invalid(signals.get("expected_salary_range_inr_lpa")),
    }


def raw_redrob_snapshot(signals: dict[str, Any]) -> dict[str, object]:
    keys = [
        "open_to_work_flag",
        "last_active_date",
        "recruiter_response_rate",
        "avg_response_time_hours",
        "notice_period_days",
        "willing_to_relocate",
        "preferred_work_mode",
        "github_activity_score",
        "search_appearance_30d",
        "saved_by_recruiters_30d",
        "interview_completion_rate",
        "offer_acceptance_rate",
        "verified_email",
        "verified_phone",
        "linkedin_connected",
    ]
    return {key: signals.get(key) for key in keys}


def compute_redrob_scorecard(
    candidate: dict[str, Any],
    as_of_date: str | date | None = None,
) -> RedrobScorecard:
    signals = candidate.get("redrob_signals")
    signals = signals if isinstance(signals, dict) else {}
    components = [
        score_activity_recency(signals, as_of_date),
        score_availability_intent(signals),
        score_recruiter_responsiveness(signals),
        score_notice_logistics(signals),
        score_market_interest(signals),
        score_process_reliability(signals),
        score_profile_trust(signals),
        score_technical_activity(signals),
    ]
    score = round_score(clamp01(sum(component.weighted_score for component in components)), 6)
    band = get_behavior_band(score)
    multiplier = get_behavior_multiplier(score)
    risk_flags = compute_redrob_risk_flags(signals, as_of_date)
    return RedrobScorecard(
        candidate_id=str(candidate.get("candidate_id", "")),
        redrob_availability_score=score,
        behavior_band=band,
        behavior_multiplier=multiplier,
        components=components,
        risk_flags=risk_flags,
        raw_snapshot=raw_redrob_snapshot(signals),
        short_summary=_short_summary(band, risk_flags, components),
    )


def redrob_scorecard_to_flat_dict(scorecard: RedrobScorecard) -> dict[str, Any]:
    row: dict[str, Any] = {
        "candidate_id": scorecard.candidate_id,
        "redrob_availability_score": scorecard.redrob_availability_score,
        "behavior_band": scorecard.behavior_band,
        "behavior_multiplier": scorecard.behavior_multiplier,
        "short_summary": scorecard.short_summary,
    }
    for component in scorecard.components:
        row[f"{component.name}_raw"] = component.raw_score
        row[f"{component.name}_weighted"] = component.weighted_score
    row.update(scorecard.risk_flags)
    row.update(scorecard.raw_snapshot)
    return row


def apply_behavior_multiplier_preview(static_fit_score: float, redrob_scorecard: RedrobScorecard) -> float:
    return round_score(clamp01(static_fit_score * redrob_scorecard.behavior_multiplier), 6)


def _short_summary(
    band: str,
    risk_flags: dict[str, bool],
    components: list[RedrobComponentScore],
) -> str:
    by_name = {component.name: component.raw_score for component in components}
    if band in {"excellent_hireability", "good_hireability"}:
        positives = []
        if by_name.get("activity_recency", 0) >= 0.75:
            positives.append("recently active")
        if by_name.get("recruiter_responsiveness", 0) >= 0.70:
            positives.append("high recruiter response")
        if by_name.get("notice_logistics", 0) >= 0.65:
            positives.append("manageable notice period")
        return f"Good hireability: {', '.join(positives) or 'strong Redrob signals'}."
    risks = [name for name, value in risk_flags.items() if value]
    if band in {"risky_hireability", "low_hireability", "very_low_hireability"} and risks:
        return f"Risky hireability: {', '.join(risks[:3]).replace('_', ' ')}."
    return "Neutral hireability: active enough but limited recruiter intent signals."


def _as_of_date(value: str | date | None) -> date | None:
    if isinstance(value, date):
        return value
    if value is None or value == DEFAULT_AS_OF_DATE:
        return DEFAULT_AS_OF_DATE_PARSED
    return parse_iso_date(value)


def _number_or_none(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _assessment_values(signals: dict[str, Any]) -> list[float]:
    scores = signals.get("skill_assessment_scores")
    if not isinstance(scores, dict):
        return []
    return [float(value) for value in scores.values() if isinstance(value, (int, float))]


def _salary_range_invalid(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    minimum = _number_or_none(value.get("min"))
    maximum = _number_or_none(value.get("max"))
    return minimum is not None and maximum is not None and minimum > maximum
