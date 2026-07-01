from __future__ import annotations

from src.ranking import RankedPreviewRow
from src.ranking_quality import evaluate_ranking_quality, format_quality_markdown


def make_row(
    index: int,
    retrieval: bool = True,
    wrong_role: bool = False,
    high_trap: bool = False,
    keyword_stuffing: bool = False,
    low_hireability: bool = False,
    production: bool = True,
) -> RankedPreviewRow:
    flags = {
        "has_real_retrieval_or_ranking_evidence": retrieval,
        "wrong_role_title": wrong_role,
        "high_or_extreme_trap_risk": high_trap,
        "keyword_stuffing_shape": keyword_stuffing,
        "low_or_very_low_hireability": low_hireability,
        "has_production_evidence": production,
    }
    return RankedPreviewRow(
        preview_rank=index,
        candidate_id=f"CAND_{index:07d}",
        final_score_preview=1 - index * 0.001,
        final_score_band="strong_fit",
        title="Engineer",
        title_category="target",
        years_of_experience=6,
        location="Pune",
        location_category="preferred",
        static_fit_score=0.8,
        redrob_availability_score=0.8,
        behavior_multiplier=1.0,
        trap_total_penalty=0.0,
        trap_penalty_multiplier=1.0,
        applied_cap_codes="",
        debug_summary="debug",
        evidence_seeds=["seed"],
        flat_debug=flags,
    )


def test_evaluate_ranking_quality_returns_report():
    rows = [make_row(index) for index in range(1, 11)]

    report = evaluate_ranking_quality(rows)

    assert report.top_k == 10
    assert report.top10_real_retrieval_evidence_count == 10


def test_warning_appears_if_top10_has_too_few_retrieval_candidates():
    rows = [make_row(index, retrieval=index <= 3) for index in range(1, 11)]

    report = evaluate_ranking_quality(rows)

    assert any("too few" in warning for warning in report.warnings)


def test_warning_appears_if_top10_has_wrong_role_candidate():
    rows = [make_row(index, wrong_role=index == 1) for index in range(1, 11)]

    report = evaluate_ranking_quality(rows)

    assert any("wrong-role" in warning for warning in report.warnings)


def test_warning_appears_if_high_extreme_trap_rate_is_too_high():
    rows = [make_row(index, high_trap=index <= 20) for index in range(1, 101)]

    report = evaluate_ranking_quality(rows)

    assert any("trap rate" in warning for warning in report.warnings)


def test_format_quality_markdown_contains_title():
    report = evaluate_ranking_quality([make_row(index) for index in range(1, 11)])

    assert "Ranking Quality Report" in format_quality_markdown(report)
