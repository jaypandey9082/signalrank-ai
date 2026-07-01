from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.load_data import iter_candidates
from src.redrob_scoring import apply_behavior_multiplier_preview, compute_redrob_scorecard
from src.schema import validate_candidate
from src.scoring import score_candidate
from src.trap_penalties import (
    apply_trap_penalty_preview,
    compute_trap_penalty_scorecard,
    trap_scorecard_to_flat_dict,
)
from src.utils import ensure_parent_dir, safe_mean, top_n_by_key


@dataclass
class TrapInspectionReport:
    total_seen: int
    scored_count: int
    scoring_error_count: int
    average_total_penalty: float
    average_penalty_multiplier: float
    severity_band_counts: dict[str, int]
    risk_flag_counts: dict[str, int]
    signal_counts: dict[str, int]
    top_risk_examples: list[dict[str, Any]]
    clean_examples: list[dict[str, Any]]
    debug_rows: list[dict[str, Any]]
    preview_rows: list[dict[str, Any]]
    warning_notes: list[str]


def inspect_traps(
    path: str | Path,
    limit: int | None = None,
    top_n: int = 25,
    include_preview: bool = False,
) -> TrapInspectionReport:
    total_seen = 0
    scored_count = 0
    scoring_error_count = 0
    severity_bands: Counter[str] = Counter()
    risk_flags: Counter[str] = Counter()
    signal_counts: Counter[str] = Counter()
    penalties: list[float] = []
    multipliers: list[float] = []
    rows: list[dict[str, Any]] = []
    preview_rows: list[dict[str, Any]] = []
    warning_notes: list[str] = []

    for candidate in iter_candidates(path):
        if limit is not None and total_seen >= limit:
            break
        total_seen += 1

        validation = validate_candidate(candidate)
        if not validation.is_valid:
            scoring_error_count += 1
            continue

        try:
            trap_scorecard = compute_trap_penalty_scorecard(candidate)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            scoring_error_count += 1
            if len(warning_notes) < 5:
                candidate_id = candidate.get("candidate_id", "<unknown>")
                warning_notes.append(f"{candidate_id}: trap scoring failed with {exc.__class__.__name__}")
            continue

        scored_count += 1
        severity_bands[trap_scorecard.severity_band] += 1
        penalties.append(trap_scorecard.total_penalty)
        multipliers.append(trap_scorecard.penalty_multiplier)
        for flag_name, flag_value in trap_scorecard.risk_flags.items():
            if flag_value:
                risk_flags[flag_name] += 1
        for signal in trap_scorecard.signals:
            signal_counts[signal.code] += 1

        row = trap_scorecard_to_flat_dict(trap_scorecard)
        row["signal_evidence"] = _signal_evidence_text(trap_scorecard.signals)
        rows.append(row)

        if include_preview and len(preview_rows) < top_n:
            static_scorecard = score_candidate(candidate)
            redrob_scorecard = compute_redrob_scorecard(candidate)
            behavior_preview = apply_behavior_multiplier_preview(
                static_scorecard.static_fit_score,
                redrob_scorecard,
            )
            preview_rows.append(
                {
                    "candidate_id": trap_scorecard.candidate_id,
                    "static_fit_score": static_scorecard.static_fit_score,
                    "redrob_availability_score": redrob_scorecard.redrob_availability_score,
                    "behavior_multiplier": redrob_scorecard.behavior_multiplier,
                    "preview_static_behavior_score": behavior_preview,
                    "trap_total_penalty": trap_scorecard.total_penalty,
                    "trap_penalty_multiplier": trap_scorecard.penalty_multiplier,
                    "preview_static_behavior_trap_score": apply_trap_penalty_preview(
                        behavior_preview,
                        trap_scorecard,
                    ),
                    "note": "preview only; not final ranking",
                }
            )

    return TrapInspectionReport(
        total_seen=total_seen,
        scored_count=scored_count,
        scoring_error_count=scoring_error_count,
        average_total_penalty=round(safe_mean(penalties), 6),
        average_penalty_multiplier=round(safe_mean(multipliers), 6),
        severity_band_counts=dict(severity_bands),
        risk_flag_counts=dict(risk_flags),
        signal_counts=dict(signal_counts),
        top_risk_examples=top_n_by_key(rows, "total_penalty", top_n, reverse=True),
        clean_examples=top_n_by_key(rows, "total_penalty", top_n, reverse=False),
        debug_rows=rows,
        preview_rows=preview_rows,
        warning_notes=warning_notes,
    )


def format_trap_console_report(report: TrapInspectionReport) -> str:
    lines = [
        "SignalRank AI Trap Inspection",
        "=============================",
        f"Total candidates seen: {report.total_seen}",
        f"Candidates scored: {report.scored_count}",
        f"Scoring errors or invalid records: {report.scoring_error_count}",
        f"Average trap penalty: {report.average_total_penalty:.4f}",
        f"Average trap multiplier: {report.average_penalty_multiplier:.4f}",
        "",
        "Severity bands:",
        _format_dict(report.severity_band_counts),
        "",
        "Risk flags:",
        _format_dict(report.risk_flag_counts),
        "",
        "Signal counts:",
        _format_dict(report.signal_counts),
        "",
        "Top trap-risk examples:",
        _format_rows(report.top_risk_examples),
        "",
        "Cleanest examples:",
        _format_rows(report.clean_examples),
    ]
    if report.preview_rows:
        lines.extend(
            [
                "",
                "Static x behavior x trap preview examples (not final ranking):",
                _format_preview_rows(report.preview_rows),
            ]
        )
    if report.warning_notes:
        lines.extend(["", "Warnings:", *[f"- {note}" for note in report.warning_notes]])
    return "\n".join(lines)


def format_trap_markdown_report(report: TrapInspectionReport) -> str:
    lines = [
        "# Trap Inspection Report",
        "",
        "This is trap inspection, not the final ranking run.",
        "",
        "## Summary",
        "",
        f"- Total candidates seen: {report.total_seen}",
        f"- Candidates scored: {report.scored_count}",
        f"- Scoring errors or invalid records: {report.scoring_error_count}",
        f"- Average trap penalty: {report.average_total_penalty:.4f}",
        f"- Average trap multiplier: {report.average_penalty_multiplier:.4f}",
        "",
        "## Severity Bands",
        _format_dict(report.severity_band_counts),
        "",
        "## Risk Flags",
        _format_dict(report.risk_flag_counts),
        "",
        "## Signal Counts",
        _format_dict(report.signal_counts),
        "",
        "## Top Trap-Risk Examples",
        _format_rows(report.top_risk_examples),
        "",
        "## Cleanest Examples",
        _format_rows(report.clean_examples),
    ]
    if report.preview_rows:
        lines.extend(
            [
                "",
                "## Static x Behavior x Trap Preview Examples",
                "",
                "These rows are preview-only and are not final ranking scores.",
                "",
                _format_preview_rows(report.preview_rows),
            ]
        )
    if report.warning_notes:
        lines.extend(["", "## Warnings", *[f"- {note}" for note in report.warning_notes]])
    return "\n".join(lines) + "\n"


def trap_rows_to_csv(rows: list[dict[str, Any]], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["candidate_id"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _signal_evidence_text(signals: list[Any], max_items: int = 5) -> str:
    evidence: list[str] = []
    for signal in signals:
        for item in signal.evidence:
            if item and item not in evidence:
                evidence.append(item)
            if len(evidence) >= max_items:
                return " | ".join(evidence)
    return " | ".join(evidence)


def _format_dict(values: dict[str, int]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {key}: {value}" for key, value in sorted(values.items()))


def _format_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- None"
    return "\n".join(
        "- "
        f"{row.get('candidate_id')} | penalty={row.get('total_penalty'):.4f} | "
        f"{row.get('severity_band')} | x{row.get('penalty_multiplier'):.2f} | "
        f"{row.get('short_summary')}"
        for row in rows
    )


def _format_preview_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- None"
    return "\n".join(
        "- "
        f"{row.get('candidate_id')} | static={row.get('static_fit_score'):.4f} | "
        f"behavior_preview={row.get('preview_static_behavior_score'):.4f} | "
        f"trap_multiplier={row.get('trap_penalty_multiplier'):.2f} | "
        f"preview={row.get('preview_static_behavior_trap_score'):.4f}"
        for row in rows
    )
