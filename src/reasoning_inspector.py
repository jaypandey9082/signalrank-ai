from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.ranking import RankedPreviewRow, rank_candidates_preview
from src.reasoning import CandidateReasoning, generate_reasoning_for_row
from src.reasoning_quality import (
    ReasoningQualityReport,
    evaluate_reasoning_quality,
    format_reasoning_quality_markdown,
)
from src.utils import ensure_parent_dir, safe_join


@dataclass
class ReasoningPreviewReport:
    total_seen: int
    ranked_count: int
    reasoned_count: int
    reasoning_error_count: int
    quality_report: ReasoningQualityReport
    preview_rows: list[dict[str, Any]]
    notes: list[str]


def build_reasoning_preview(
    path: str | Path,
    top_k: int = 100,
    limit: int | None = None,
) -> ReasoningPreviewReport:
    ranking_result = rank_candidates_preview(path, top_k=top_k, limit=limit)
    reasonings: list[CandidateReasoning] = []
    reasoning_error_count = 0
    notes = list(ranking_result.warnings)

    for row in ranking_result.rows:
        try:
            reasonings.append(generate_reasoning_for_row(row))
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            reasoning_error_count += 1
            if len(notes) < 5:
                notes.append(f"{row.candidate_id}: reasoning failed with {exc.__class__.__name__}")

    quality = evaluate_reasoning_quality(ranking_result.rows, reasonings)
    preview_rows = reasoning_preview_rows_to_dicts(ranking_result.rows, reasonings)
    return ReasoningPreviewReport(
        total_seen=ranking_result.total_seen,
        ranked_count=ranking_result.ranked_count,
        reasoned_count=len(reasonings),
        reasoning_error_count=reasoning_error_count,
        quality_report=quality,
        preview_rows=preview_rows,
        notes=notes,
    )


def reasoning_preview_rows_to_dicts(
    rows: list[RankedPreviewRow],
    reasonings: list[CandidateReasoning],
) -> list[dict[str, Any]]:
    by_id = {reasoning.candidate_id: reasoning for reasoning in reasonings}
    output: list[dict[str, Any]] = []
    for row in rows:
        reasoning = by_id.get(row.candidate_id)
        output.append(
            {
                "preview_rank": row.preview_rank,
                "candidate_id": row.candidate_id,
                "final_score_preview": row.final_score_preview,
                "final_score_band": row.final_score_band,
                "title": row.title,
                "years_of_experience": row.years_of_experience,
                "location": row.location,
                "reasoning_preview": reasoning.reasoning if reasoning else "",
                "tone": reasoning.tone if reasoning else "",
                "facts_used": safe_join(reasoning.facts_used if reasoning else []),
                "concerns_used": safe_join(reasoning.concerns_used if reasoning else []),
                "jd_terms_used": safe_join(reasoning.jd_terms_used if reasoning else []),
                "quality_flags": str(reasoning.quality_flags if reasoning else {}),
                "debug_summary": row.debug_summary,
            }
        )
    return output


def write_reasoning_preview_csv(rows: list[dict[str, Any]], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else [
        "preview_rank",
        "candidate_id",
        "reasoning_preview",
    ]
    preferred = ["preview_rank", "candidate_id", "final_score_preview", "reasoning_preview"]
    ordered = preferred + [name for name in fieldnames if name not in preferred]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ordered)
        writer.writeheader()
        writer.writerows(rows)


def format_reasoning_console_report(report: ReasoningPreviewReport, max_rows: int = 20) -> str:
    lines = [
        "SignalRank AI Reasoning Preview",
        "===============================",
        f"Total candidates seen: {report.total_seen}",
        f"Ranked preview rows: {report.ranked_count}",
        f"Reasoned rows: {report.reasoned_count}",
        f"Reasoning errors: {report.reasoning_error_count}",
        f"Quality summary: {report.quality_report.summary}",
        "",
        "Top reasoning previews:",
        _format_rows(report.preview_rows[:max_rows]),
    ]
    if report.notes:
        lines.extend(["", "Notes:", *[f"- {note}" for note in report.notes]])
    return "\n".join(lines)


def format_reasoning_markdown_report(report: ReasoningPreviewReport, max_rows: int = 50) -> str:
    lines = [
        "# Reasoning Preview Report",
        "",
        "This is a reasoning preview, not the final challenge submission.",
        "",
        "## Summary",
        "",
        f"- Total candidates seen: {report.total_seen}",
        f"- Ranked preview rows: {report.ranked_count}",
        f"- Reasoned rows: {report.reasoned_count}",
        f"- Reasoning errors: {report.reasoning_error_count}",
        f"- Quality summary: {report.quality_report.summary}",
        "",
        "## Top Reasoning Previews",
        _format_rows(report.preview_rows[:max_rows]),
        "",
        "## Quality Snapshot",
        format_reasoning_quality_markdown(report.quality_report),
    ]
    if report.notes:
        lines.extend(["", "## Notes", *[f"- {note}" for note in report.notes]])
    return "\n".join(lines) + "\n"


def _format_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- None"
    return "\n".join(
        "- "
        f"#{row.get('preview_rank')} {row.get('candidate_id')} | "
        f"{row.get('final_score_preview'):.4f} | {row.get('title')} | "
        f"{row.get('reasoning_preview')}"
        for row in rows
    )
