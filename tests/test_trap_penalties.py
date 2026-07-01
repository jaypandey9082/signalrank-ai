from __future__ import annotations

from copy import deepcopy

from src.trap_penalties import (
    apply_trap_penalty_preview,
    compute_trap_penalty_scorecard,
    trap_scorecard_to_flat_dict,
)
from tests.test_schema import make_candidate


def strong_candidate() -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = "CAND_0000301"
    candidate["profile"].update(
        {
            "current_title": "Senior AI Engineer",
            "headline": "Senior AI engineer for search and ranking systems",
            "summary": "Built production retrieval, ranking, embedding, and evaluation systems.",
            "years_of_experience": 7,
        }
    )
    candidate["career_history"][0].update(
        {
            "title": "Senior AI Engineer",
            "description": "Owned production semantic search, learning to rank, embeddings, and offline NDCG evaluation.",
            "duration_months": 84,
        }
    )
    candidate["skills"].extend(
        [
            {"name": "Vector Search", "proficiency": "advanced", "endorsements": 18, "duration_months": 36},
            {"name": "NDCG", "proficiency": "advanced", "endorsements": 12, "duration_months": 30},
        ]
    )
    return candidate


def wrong_role_keyword_candidate() -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = "CAND_0000302"
    candidate["profile"].update(
        {
            "current_title": "Marketing Manager",
            "headline": "AI expert and growth leader",
            "summary": "Prompt engineering, ChatGPT, GenAI, vector search, ranking, embeddings.",
        }
    )
    candidate["career_history"][0].update(
        {
            "title": "Marketing Manager",
            "industry": "Marketing",
            "description": "Ran campaigns and brand strategy.",
        }
    )
    candidate["skills"] = [
        {"name": "Prompt Engineering", "proficiency": "expert", "endorsements": 1, "duration_months": 0},
        {"name": "ChatGPT", "proficiency": "expert", "endorsements": 1, "duration_months": 0},
        {"name": "Vector Search", "proficiency": "expert", "endorsements": 1, "duration_months": 0},
        {"name": "Learning to Rank", "proficiency": "expert", "endorsements": 1, "duration_months": 0},
    ]
    return candidate


def test_strong_candidate_has_low_or_no_penalty():
    scorecard = compute_trap_penalty_scorecard(strong_candidate())

    assert scorecard.total_penalty < 0.05
    assert scorecard.severity_band == "clean"


def test_keyword_stuffed_wrong_role_gets_high_or_extreme_penalty():
    scorecard = compute_trap_penalty_scorecard(wrong_role_keyword_candidate())

    assert scorecard.total_penalty >= 0.30
    assert scorecard.severity_band in {"high_risk", "extreme_risk"}
    assert scorecard.risk_flags["wrong_role_keyword_stuffing"]
    assert scorecard.risk_flags["honeypot_like_profile_shape"]


def test_weak_ai_hype_without_production_is_flagged():
    candidate = make_candidate()
    candidate["profile"]["summary"] = "Built AI agents and prompt engineering demos."
    candidate["career_history"][0]["description"] = "Built internal GenAI demos."
    candidate["skills"] = [{"name": "Prompt Engineering", "proficiency": "advanced", "endorsements": 5, "duration_months": 6}]

    scorecard = compute_trap_penalty_scorecard(candidate)

    assert scorecard.risk_flags["weak_ai_hype_without_production"]


def test_consulting_only_no_product_is_flagged():
    candidate = make_candidate()
    candidate["profile"]["current_company"] = "ConsultingCo"
    candidate["profile"]["current_industry"] = "IT Services"
    candidate["career_history"] = [
        {
            "company": "ConsultingCo",
            "title": "Machine Learning Engineer",
            "start_date": "2020-01-01",
            "end_date": None,
            "duration_months": 60,
            "is_current": True,
            "industry": "IT Services",
            "company_size": "501-1000",
            "description": "Delivered client analytics dashboards and model prototypes.",
        }
    ]

    scorecard = compute_trap_penalty_scorecard(candidate)

    assert scorecard.risk_flags["consulting_only_no_product"]


def test_non_target_ai_only_is_flagged():
    candidate = make_candidate()
    candidate["career_history"][0]["description"] = "Built computer vision and robotics perception systems."
    candidate["skills"] = [
        {"name": "Computer Vision", "proficiency": "expert", "endorsements": 10, "duration_months": 48},
        {"name": "Robotics", "proficiency": "advanced", "endorsements": 8, "duration_months": 36},
    ]

    scorecard = compute_trap_penalty_scorecard(candidate)

    assert scorecard.risk_flags["non_target_ai_only"]


def test_expert_skill_zero_duration_is_flagged():
    candidate = make_candidate()
    candidate["skills"].append({"name": "Vector Search", "proficiency": "expert", "endorsements": 2, "duration_months": 0})

    scorecard = compute_trap_penalty_scorecard(candidate)

    assert scorecard.risk_flags["expert_skill_zero_duration"]


def test_salary_min_greater_than_max_is_profile_inconsistency():
    candidate = make_candidate()
    candidate["redrob_signals"]["expected_salary_range_inr_lpa"] = {"min": 80, "max": 50}

    scorecard = compute_trap_penalty_scorecard(candidate)

    assert scorecard.risk_flags["profile_data_inconsistency"]


def test_last_active_before_signup_is_platform_inconsistency():
    candidate = make_candidate()
    candidate["redrob_signals"]["signup_date"] = "2026-06-01"
    candidate["redrob_signals"]["last_active_date"] = "2026-01-01"

    scorecard = compute_trap_penalty_scorecard(candidate)

    assert scorecard.risk_flags["platform_data_inconsistency"]


def test_severe_low_availability_is_flagged():
    candidate = make_candidate()
    candidate["redrob_signals"].update(
        {
            "last_active_date": "2025-01-01",
            "open_to_work_flag": False,
            "recruiter_response_rate": 0.05,
            "avg_response_time_hours": 240,
            "notice_period_days": 150,
        }
    )

    scorecard = compute_trap_penalty_scorecard(candidate)

    assert scorecard.risk_flags["severe_low_availability"]


def test_flat_dict_and_preview_clamp():
    scorecard = compute_trap_penalty_scorecard(wrong_role_keyword_candidate())
    flat = trap_scorecard_to_flat_dict(scorecard)

    assert flat["candidate_id"] == "CAND_0000302"
    assert "total_penalty" in flat
    assert apply_trap_penalty_preview(2.0, scorecard) <= 1.0


def test_input_candidate_is_not_mutated():
    candidate = wrong_role_keyword_candidate()
    before = deepcopy(candidate)

    compute_trap_penalty_scorecard(candidate)

    assert candidate == before
