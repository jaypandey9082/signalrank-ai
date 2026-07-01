from __future__ import annotations

from dataclasses import dataclass

from src.ranking import RankedPreviewRow
from src.scoring_config import RANKING_QUALITY_THRESHOLDS
from src.utils import safe_percent


@dataclass
class RankingQualityReport:
    top_k: int
    top10_real_retrieval_evidence_count: int
    top10_wrong_role_count: int
    top10_high_or_extreme_trap_count: int
    top100_high_or_extreme_trap_rate: float
    top100_keyword_stuffing_rate: float
    top100_low_hireability_count: int
    top100_without_production_evidence_count: int
    warnings: list[str]
    summary: str


def evaluate_ranking_quality(rows: list[RankedPreviewRow]) -> RankingQualityReport:
    top10 = rows[:10]
    top100 = rows[:100]
    top10_real_retrieval = _count_true(top10, "has_real_retrieval_or_ranking_evidence")
    top10_wrong_role = _count_true(top10, "wrong_role_title")
    top10_high_or_extreme = _count_true(top10, "high_or_extreme_trap_risk")
    top100_high_or_extreme = _count_true(top100, "high_or_extreme_trap_risk")
    top100_keyword_stuffing = _count_true(top100, "keyword_stuffing_shape")
    top100_low_hireability = _count_true(top100, "low_or_very_low_hireability")
    top100_without_production = sum(
        1 for row in top100 if not bool(row.flat_debug.get("has_production_evidence"))
    )

    high_or_extreme_rate = safe_percent(top100_high_or_extreme, len(top100))
    keyword_stuffing_rate = safe_percent(top100_keyword_stuffing, len(top100))
    warnings: list[str] = []
    thresholds = RANKING_QUALITY_THRESHOLDS
    if len(top10) >= 10 and top10_real_retrieval < thresholds["top10_min_real_retrieval_evidence"]:
        warnings.append(
            "Top 10 has too few candidates with real retrieval/ranking evidence "
            f"({top10_real_retrieval}/10)."
        )
    if top10_wrong_role > thresholds["top10_max_wrong_role_titles"]:
        warnings.append(f"Top 10 contains wrong-role candidates ({top10_wrong_role}).")
    if high_or_extreme_rate > thresholds["top100_max_high_or_extreme_trap_rate"]:
        warnings.append(f"Top 100 high/extreme trap rate is high ({high_or_extreme_rate:.2%}).")
    if keyword_stuffing_rate > thresholds["top100_max_keyword_stuffing_rate"]:
        warnings.append(f"Top 100 keyword-stuffing rate is high ({keyword_stuffing_rate:.2%}).")

    summary = "Ranking quality checks passed." if not warnings else "Ranking quality warnings need review."
    return RankingQualityReport(
        top_k=len(rows),
        top10_real_retrieval_evidence_count=top10_real_retrieval,
        top10_wrong_role_count=top10_wrong_role,
        top10_high_or_extreme_trap_count=top10_high_or_extreme,
        top100_high_or_extreme_trap_rate=round(high_or_extreme_rate, 6),
        top100_keyword_stuffing_rate=round(keyword_stuffing_rate, 6),
        top100_low_hireability_count=top100_low_hireability,
        top100_without_production_evidence_count=top100_without_production,
        warnings=warnings,
        summary=summary,
    )


def format_quality_markdown(report: RankingQualityReport) -> str:
    lines = [
        "# Ranking Quality Report",
        "",
        f"- Rows evaluated: {report.top_k}",
        f"- Top 10 real retrieval evidence count: {report.top10_real_retrieval_evidence_count}",
        f"- Top 10 wrong-role count: {report.top10_wrong_role_count}",
        f"- Top 10 high/extreme trap count: {report.top10_high_or_extreme_trap_count}",
        f"- Top 100 high/extreme trap rate: {report.top100_high_or_extreme_trap_rate:.2%}",
        f"- Top 100 keyword-stuffing rate: {report.top100_keyword_stuffing_rate:.2%}",
        f"- Top 100 low hireability count: {report.top100_low_hireability_count}",
        f"- Top 100 without production evidence count: {report.top100_without_production_evidence_count}",
        "",
        f"Summary: {report.summary}",
    ]
    if report.warnings:
        lines.extend(["", "## Warnings", *[f"- {warning}" for warning in report.warnings]])
    return "\n".join(lines) + "\n"


def _count_true(rows: list[RankedPreviewRow], flag_name: str) -> int:
    return sum(1 for row in rows if bool(row.flat_debug.get(flag_name)))
