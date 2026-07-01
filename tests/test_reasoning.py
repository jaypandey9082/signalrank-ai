from __future__ import annotations

from src.ranking import RankedPreviewRow
from src.reasoning import (
    ReasoningInput,
    clean_reason_text,
    generate_reasoning_for_row,
    generate_reasoning_from_input,
    split_applied_caps,
    years_text,
)


def strong_input() -> ReasoningInput:
    return ReasoningInput(
        candidate_id="CAND_0001001",
        preview_rank=1,
        final_score_preview=0.86,
        final_score_band="elite_fit",
        title="Recommendation Systems Engineer",
        title_category="target",
        years_of_experience=6.5,
        location="Pune",
        location_category="preferred",
        static_fit_score=0.82,
        redrob_availability_score=0.80,
        behavior_band="good_hireability",
        trap_severity_band="clean",
        applied_cap_codes=[],
        evidence_seeds=[
            "title: Recommendation Systems Engineer",
            "experience: 6.5 years",
            "Shipped production ranking model for search relevance using FAISS retrieval.",
            "Measured NDCG, MRR, and A/B test results for real users.",
        ],
        key_flags={
            "has_real_retrieval_or_ranking_evidence": True,
            "has_evaluation_evidence": True,
            "has_production_evidence": True,
            "wrong_role_title": False,
            "keyword_stuffing_shape": False,
            "low_or_very_low_hireability": False,
            "high_or_extreme_trap_risk": False,
        },
        debug_summary="static fit includes retrieval/ranking evidence; good hireability",
    )


def risky_input() -> ReasoningInput:
    return ReasoningInput(
        candidate_id="CAND_0001002",
        preview_rank=90,
        final_score_preview=0.12,
        final_score_band="weak_fit",
        title="Marketing Manager",
        title_category="wrong_role",
        years_of_experience=5,
        location="Delhi",
        location_category="acceptable",
        static_fit_score=0.20,
        redrob_availability_score=0.30,
        behavior_band="low_hireability",
        trap_severity_band="high_risk",
        applied_cap_codes=["wrong_role_keyword_stuffing", "weak_ai_hype_without_production"],
        evidence_seeds=[
            "title: Marketing Manager",
            "experience: 5 years",
            "Risky Hireability: low recruiter response rate.",
        ],
        key_flags={
            "has_real_retrieval_or_ranking_evidence": False,
            "has_evaluation_evidence": False,
            "has_production_evidence": False,
            "wrong_role_title": True,
            "keyword_stuffing_shape": True,
            "low_or_very_low_hireability": True,
            "high_or_extreme_trap_risk": True,
        },
        debug_summary="limited production retrieval evidence; capped by wrong_role_keyword_stuffing",
    )


def make_row(input_value: ReasoningInput) -> RankedPreviewRow:
    flat = {
        "behavior_band": input_value.behavior_band,
        "trap_severity_band": input_value.trap_severity_band,
        "applied_cap_codes": ", ".join(input_value.applied_cap_codes),
        **input_value.key_flags,
    }
    return RankedPreviewRow(
        preview_rank=input_value.preview_rank or 0,
        candidate_id=input_value.candidate_id,
        final_score_preview=input_value.final_score_preview,
        final_score_band=input_value.final_score_band,
        title=input_value.title,
        title_category=input_value.title_category,
        years_of_experience=input_value.years_of_experience,
        location=input_value.location,
        location_category=input_value.location_category,
        static_fit_score=input_value.static_fit_score,
        redrob_availability_score=input_value.redrob_availability_score,
        behavior_multiplier=1.0,
        trap_total_penalty=0.0,
        trap_penalty_multiplier=1.0,
        applied_cap_codes=", ".join(input_value.applied_cap_codes),
        debug_summary=input_value.debug_summary,
        evidence_seeds=input_value.evidence_seeds,
        flat_debug=flat,
    )


def test_generate_reasoning_from_input_returns_non_empty_reasoning():
    reasoning = generate_reasoning_from_input(strong_input())

    assert reasoning.reasoning


def test_reasoning_is_at_most_two_sentences():
    reasoning = generate_reasoning_from_input(strong_input())

    assert reasoning.reasoning.count(".") <= 2


def test_strong_candidate_reasoning_has_specific_facts_and_jd_terms():
    reasoning = generate_reasoning_from_input(strong_input())
    text = reasoning.reasoning.lower()

    assert "ranking" in text or "retrieval" in text or "evaluation" in text
    assert "6.5 years" in text or "faiss" in text or "ndcg" in text


def test_risky_candidate_reasoning_includes_concern_and_does_not_oversell():
    reasoning = generate_reasoning_from_input(risky_input())

    assert "Concern:" in reasoning.reasoning
    assert "Strong fit" not in reasoning.reasoning
    assert "elite" not in reasoning.reasoning.lower()
    assert "production ML" not in reasoning.reasoning


def test_internal_debug_terms_do_not_appear():
    reasoning = generate_reasoning_from_input(risky_input())
    lowered = reasoning.reasoning.lower()

    assert "final_score_preview" not in lowered
    assert "guardrail" not in lowered
    assert "scorecard" not in lowered
    assert "confirmed honeypot" not in lowered


def test_clean_reason_text_removes_newlines_and_outer_quotes():
    assert clean_reason_text('"hello\\n world"') == "hello\\n world"
    assert clean_reason_text('"hello\n world"') == "hello world"


def test_years_text_formats_years():
    assert years_text(6.5) == "6.5 years"
    assert years_text(6) == "6 years"
    assert years_text(None) == "unknown experience"


def test_split_applied_caps_handles_list_and_string():
    assert split_applied_caps(["a", "b"]) == ["a", "b"]
    assert split_applied_caps("a, b, a") == ["a", "b"]


def test_generate_reasoning_for_row_works_with_ranked_row():
    reasoning = generate_reasoning_for_row(make_row(strong_input()))

    assert reasoning.candidate_id == "CAND_0001001"
    assert reasoning.reasoning
