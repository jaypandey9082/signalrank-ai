from __future__ import annotations

from src.reasoning import CandidateReasoning
from src.reasoning_quality import (
    count_sentences,
    evaluate_reasoning_quality,
    format_reasoning_quality_markdown,
    has_jd_connection,
    has_specific_fact,
    is_too_generic,
)
from tests.test_reasoning import make_row, risky_input, strong_input


def make_reasoning(candidate_id: str, text: str, tone: str = "strong") -> CandidateReasoning:
    return CandidateReasoning(
        candidate_id=candidate_id,
        reasoning=text,
        tone=tone,
        facts_used=[],
        concerns_used=[],
        jd_terms_used=[],
        quality_flags={},
    )


def test_count_sentences_works():
    assert count_sentences("One. Two!") == 2


def test_is_too_generic_detects_generic_phrase():
    assert is_too_generic("Strong candidate with relevant skills.")


def test_has_jd_connection_detects_ranking_terms():
    assert has_jd_connection("Maps to the ranking/search focus.")


def test_has_specific_fact_detects_years_tools_and_metrics():
    assert has_specific_fact("6.5 years with FAISS and NDCG.")


def test_evaluate_reasoning_quality_catches_empty_reasoning():
    row = make_row(strong_input())
    report = evaluate_reasoning_quality([row], [make_reasoning(row.candidate_id, "")])

    assert report.empty_count == 1


def test_evaluate_reasoning_quality_catches_repeated_reasoning():
    row1 = make_row(strong_input())
    row2 = make_row(risky_input())
    text = "6.5 years with production ranking/search evidence for the JD."
    report = evaluate_reasoning_quality(
        [row1, row2],
        [make_reasoning(row1.candidate_id, text), make_reasoning(row2.candidate_id, text)],
    )

    assert report.repeated_reasoning_count == 2


def test_evaluate_reasoning_quality_catches_missing_jd_connection():
    row = make_row(strong_input())
    report = evaluate_reasoning_quality([row], [make_reasoning(row.candidate_id, "6.5 years in Pune.")])

    assert report.missing_jd_connection_count == 1


def test_evaluate_reasoning_quality_catches_too_long_reasoning():
    row = make_row(strong_input())
    long_text = "Ranking/search " + "x" * 520
    report = evaluate_reasoning_quality([row], [make_reasoning(row.candidate_id, long_text)])

    assert report.too_long_count == 1


def test_format_reasoning_quality_markdown_contains_title():
    row = make_row(strong_input())
    report = evaluate_reasoning_quality(
        [row],
        [make_reasoning(row.candidate_id, "6.5 years with production ranking/search evidence.")],
    )

    assert "Reasoning Quality Report" in format_reasoning_quality_markdown(report)
