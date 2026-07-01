from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.submission import SubmissionBuildResult
from src.submission_validator import SubmissionValidationReport
from src.utils import ensure_parent_dir, format_elapsed


@dataclass
class RuntimeReport:
    generated_at: str
    candidates_path: str
    output_csv: str
    output_xlsx: str | None
    total_seen: int
    valid_count: int
    submitted_count: int
    elapsed_seconds: float
    validation_summary: str
    ranking_quality_summary: str
    reasoning_quality_summary: str
    warnings: list[str]
    top_rows_preview: list[dict[str, Any]]


def build_runtime_report(
    result: SubmissionBuildResult,
    candidates_path: str | Path,
    output_csv: str | Path,
    output_xlsx: str | Path | None,
    validation_report: SubmissionValidationReport,
    top_preview_count: int = 10,
) -> RuntimeReport:
    validation_summary = (
        f"valid={validation_report.is_valid}, "
        f"errors={validation_report.error_count}, warnings={validation_report.warning_count}"
    )
    return RuntimeReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        candidates_path=str(candidates_path),
        output_csv=str(output_csv),
        output_xlsx=str(output_xlsx) if output_xlsx else None,
        total_seen=result.total_seen,
        valid_count=result.valid_count,
        submitted_count=result.submitted_count,
        elapsed_seconds=result.elapsed_seconds,
        validation_summary=validation_summary,
        ranking_quality_summary=result.ranking_quality_summary,
        reasoning_quality_summary=result.reasoning_quality_summary,
        warnings=result.warnings,
        top_rows_preview=result.debug_rows[:top_preview_count],
    )


def runtime_report_to_markdown(report: RuntimeReport) -> str:
    lines = [
        "# Submission Run Report",
        "",
        f"- Generated at: {report.generated_at}",
        f"- Candidates path: `{report.candidates_path}`",
        f"- Output CSV: `{report.output_csv}`",
        f"- Output XLSX: `{report.output_xlsx or '<not requested>'}`",
        f"- Total seen: {report.total_seen}",
        f"- Valid count: {report.valid_count}",
        f"- Submitted count: {report.submitted_count}",
        f"- Elapsed: {format_elapsed(report.elapsed_seconds)}",
        f"- Validation: {report.validation_summary}",
        f"- Ranking quality: {report.ranking_quality_summary}",
        f"- Reasoning quality: {report.reasoning_quality_summary}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {warning}" for warning in report.warnings) if report.warnings else lines.append("- None")
    lines.extend(["", "## Top Rows Preview", "", "| Rank | Candidate | Score | Reasoning |", "|---:|---|---:|---|"])
    for row in report.top_rows_preview:
        reasoning = str(row.get("reasoning", ""))
        short = reasoning[:180] + "..." if len(reasoning) > 180 else reasoning
        lines.append(f"| {row.get('rank')} | {row.get('candidate_id')} | {row.get('score')} | {short} |")
    return "\n".join(lines) + "\n"


def write_runtime_report(report: RuntimeReport, out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    output_path.write_text(runtime_report_to_markdown(report), encoding="utf-8")
