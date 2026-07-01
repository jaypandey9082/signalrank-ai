from __future__ import annotations

from src.combined_scoring import (
    apply_caps,
    combined_scorecard_to_flat_dict,
    compute_combined_scorecard,
    make_guardrail_cap,
)
from tests.test_schema import make_candidate
from tests.test_scoring import make_keyword_stuffer, make_strong_candidate


def test_compute_combined_scorecard_returns_score_between_zero_and_one():
    scorecard = compute_combined_scorecard(make_strong_candidate())

    assert 0 <= scorecard.final_score <= 1
    assert scorecard.final_score_band != "unknown"


def test_strong_candidate_scores_higher_than_wrong_role_keyword_stuffer():
    strong = compute_combined_scorecard(make_strong_candidate())
    weak = compute_combined_scorecard(make_keyword_stuffer())

    assert strong.final_score > weak.final_score


def test_behavior_multiplier_changes_score_but_does_not_overpower_static_fit():
    strong = make_strong_candidate()
    strong["redrob_signals"].update(
        {
            "last_active_date": "2025-01-01",
            "open_to_work_flag": False,
            "recruiter_response_rate": 0.05,
            "avg_response_time_hours": 240,
            "notice_period_days": 150,
        }
    )
    weak = make_keyword_stuffer()
    weak["redrob_signals"].update(
        {
            "last_active_date": "2026-06-30",
            "open_to_work_flag": True,
            "recruiter_response_rate": 0.95,
            "avg_response_time_hours": 8,
            "notice_period_days": 15,
        }
    )

    strong_scorecard = compute_combined_scorecard(strong)
    weak_scorecard = compute_combined_scorecard(weak)

    assert strong_scorecard.behavior_multiplier < weak_scorecard.behavior_multiplier
    assert strong_scorecard.final_score > weak_scorecard.final_score


def test_trap_penalty_multiplier_reduces_risky_candidate_score():
    scorecard = compute_combined_scorecard(make_keyword_stuffer())

    assert scorecard.trap_penalty_multiplier < 1
    assert scorecard.final_score <= scorecard.static_fit_score


def test_wrong_role_keyword_stuffing_cap_is_applied():
    scorecard = compute_combined_scorecard(make_keyword_stuffer())
    cap_codes = [cap.code for cap in scorecard.applied_caps]

    assert "wrong_role_keyword_stuffing" in cap_codes
    assert scorecard.final_score <= 0.30


def test_no_real_retrieval_or_ranking_evidence_cap_is_applied():
    candidate = make_candidate()
    candidate["profile"]["current_title"] = "Backend Engineer"
    candidate["career_history"][0]["title"] = "Backend Engineer"
    candidate["career_history"][0]["description"] = "Built APIs, data pipelines, dashboards, and batch jobs."
    candidate["skills"] = [{"name": "Python", "proficiency": "advanced", "endorsements": 8, "duration_months": 48}]

    scorecard = compute_combined_scorecard(candidate)
    cap_codes = [cap.code for cap in scorecard.applied_caps]

    assert "no_real_retrieval_or_ranking_evidence" in cap_codes
    assert scorecard.final_score <= 0.58


def test_high_or_extreme_trap_cap_lowers_final_score():
    scorecard = compute_combined_scorecard(make_keyword_stuffer())
    cap_codes = [cap.code for cap in scorecard.applied_caps]

    assert {"high_trap_risk", "extreme_trap_risk"} & set(cap_codes)
    assert scorecard.score_after_caps <= scorecard.score_before_caps


def test_evidence_seeds_are_factual_and_non_empty_for_strong_candidate():
    scorecard = compute_combined_scorecard(make_strong_candidate())

    assert scorecard.evidence_seeds
    assert any("Recommendation" in seed or "ranking" in seed for seed in scorecard.evidence_seeds)


def test_flat_dict_contains_preview_columns_and_caps():
    scorecard = compute_combined_scorecard(make_keyword_stuffer())
    flat = combined_scorecard_to_flat_dict(scorecard)

    assert "final_score_preview" in flat
    assert "applied_cap_codes" in flat
    assert flat["final_score_band"] != "unknown"


def test_apply_caps_uses_lowest_applied_cap():
    score, applied = apply_caps(
        0.90,
        [
            make_guardrail_cap("cap_a", 0.60, True),
            make_guardrail_cap("cap_b", 0.40, True),
            make_guardrail_cap("cap_c", 0.20, False),
        ],
    )

    assert score == 0.40
    assert [cap.code for cap in applied] == ["cap_a", "cap_b"]
