from __future__ import annotations

from src.redrob_scoring import (
    apply_behavior_multiplier_preview,
    compute_redrob_risk_flags,
    compute_redrob_scorecard,
    days_since,
    parse_iso_date,
    redrob_scorecard_to_flat_dict,
    score_activity_recency,
    score_market_interest,
    score_notice_logistics,
    score_recruiter_responsiveness,
    score_technical_activity,
)
from src.scoring_config import DEFAULT_AS_OF_DATE, validate_redrob_weights
from tests.test_schema import make_candidate


def good_behavior_candidate() -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = "CAND_0000201"
    candidate["redrob_signals"].update(
        {
            "last_active_date": "2026-06-28",
            "open_to_work_flag": True,
            "applications_submitted_30d": 4,
            "recruiter_response_rate": 0.90,
            "avg_response_time_hours": 12,
            "notice_period_days": 30,
            "willing_to_relocate": True,
            "preferred_work_mode": "hybrid",
            "profile_views_received_30d": 80,
            "search_appearance_30d": 220,
            "saved_by_recruiters_30d": 10,
            "interview_completion_rate": 0.90,
            "offer_acceptance_rate": 0.70,
        }
    )
    return candidate


def poor_behavior_candidate() -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = "CAND_0000202"
    candidate["redrob_signals"].update(
        {
            "signup_date": "2025-01-01",
            "last_active_date": "2025-10-01",
            "open_to_work_flag": False,
            "applications_submitted_30d": 0,
            "recruiter_response_rate": 0.05,
            "avg_response_time_hours": 220,
            "notice_period_days": 150,
            "willing_to_relocate": False,
            "preferred_work_mode": "remote",
            "profile_views_received_30d": 0,
            "search_appearance_30d": 3,
            "saved_by_recruiters_30d": 0,
            "interview_completion_rate": 0.30,
            "offer_acceptance_rate": -1,
            "verified_email": False,
            "verified_phone": False,
            "linkedin_connected": False,
        }
    )
    return candidate


def test_validate_redrob_weights_returns_true():
    assert validate_redrob_weights()


def test_parse_iso_date_works_and_handles_invalid_values():
    assert parse_iso_date("2026-07-01").isoformat() == "2026-07-01"
    assert parse_iso_date("not-date") is None
    assert parse_iso_date(None) is None


def test_days_since_uses_default_as_of_date():
    assert days_since("2026-06-01", DEFAULT_AS_OF_DATE) == 30


def test_recent_active_candidate_scores_higher_than_inactive_candidate():
    good = score_activity_recency(good_behavior_candidate()["redrob_signals"])
    poor = score_activity_recency(poor_behavior_candidate()["redrob_signals"])

    assert good.raw_score > poor.raw_score


def test_high_recruiter_response_scores_higher_than_low_slow_response():
    good = score_recruiter_responsiveness(good_behavior_candidate()["redrob_signals"])
    poor = score_recruiter_responsiveness(poor_behavior_candidate()["redrob_signals"])

    assert good.raw_score > poor.raw_score


def test_short_notice_scores_higher_than_long_notice():
    good = score_notice_logistics(good_behavior_candidate()["redrob_signals"])
    poor = score_notice_logistics(poor_behavior_candidate()["redrob_signals"])

    assert good.raw_score > poor.raw_score


def test_score_market_interest_handles_missing_values_safely():
    component = score_market_interest({})

    assert component.raw_score == 0.0


def test_github_minus_one_does_not_make_technical_activity_zero():
    signals = {"github_activity_score": -1, "skill_assessment_scores": {}}
    component = score_technical_activity(signals)

    assert component.raw_score > 0


def test_compute_redrob_risk_flags_detects_expected_flags():
    signals = poor_behavior_candidate()["redrob_signals"]
    signals["signup_date"] = "2026-01-01"
    signals["last_active_date"] = "2025-01-01"
    signals["expected_salary_range_inr_lpa"] = {"min": 50, "max": 30}

    flags = compute_redrob_risk_flags(signals)

    assert flags["inactive_180d"]
    assert flags["low_recruiter_response_rate"]
    assert flags["very_slow_response"]
    assert flags["high_notice_period"]
    assert flags["platform_dates_invalid"]
    assert flags["salary_range_invalid"]


def test_compute_redrob_scorecard_returns_score_between_zero_and_one():
    scorecard = compute_redrob_scorecard(good_behavior_candidate())

    assert 0 <= scorecard.redrob_availability_score <= 1


def test_behavior_multiplier_stays_in_expected_bounds():
    scorecard = compute_redrob_scorecard(good_behavior_candidate())

    assert 0.78 <= scorecard.behavior_multiplier <= 1.08


def test_flat_dict_includes_candidate_id_and_behavior_multiplier():
    scorecard = compute_redrob_scorecard(good_behavior_candidate())
    flat = redrob_scorecard_to_flat_dict(scorecard)

    assert flat["candidate_id"] == "CAND_0000201"
    assert "behavior_multiplier" in flat


def test_apply_behavior_multiplier_preview_clamps_between_zero_and_one():
    scorecard = compute_redrob_scorecard(good_behavior_candidate())

    assert apply_behavior_multiplier_preview(2.0, scorecard) == 1.0


def test_good_behavior_scores_higher_than_poor_behavior():
    good = compute_redrob_scorecard(good_behavior_candidate())
    poor = compute_redrob_scorecard(poor_behavior_candidate())

    assert good.redrob_availability_score > poor.redrob_availability_score
    assert good.behavior_multiplier > poor.behavior_multiplier
