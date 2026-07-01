from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from src.load_data import iter_candidates
from src.schema import validate_candidate
from src.scoring import (
    component_evidence_text,
    score_candidate,
    scorecard_to_flat_dict,
)
from src.utils import ensure_parent_dir, top_n_by_key


@dataclass
class ScoreInspectionReport:
    total_seen: int
    scored_count: int
    scoring_error_count: int
    score_band_counts: dict[str, int]
    average_static_fit_score: float
    top_debug_rows: list[dict[str, Any]]
    bottom_debug_rows: list[dict[str, Any]]
    component_averages: dict[str, float]
    strong_fit_examples: list[dict[str, Any]]
    weak_fit_examples: list[dict[str, Any]]
    warning_notes: list[str]


def inspect_scores(
    path: str | Path,
    limit: int | None = None,
    top_n: int = 20,
) -> ScoreInspectionReport:
    total_seen = 0
    scored_count = 0
    scoring_error_count = 0
    score_bands: Counter[str] = Counter()
    scores: list[float] = []
    debug_rows: list[dict[str, Any]] = []
    component_raw_scores: dict[str, list[float]] = defaultdict(list)
    strong_examples: list[dict[str, Any]] = []
    weak_examples: list[dict[str, Any]] = []
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
            scorecard = score_candidate(candidate)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            scoring_error_count += 1
            if len(warning_notes) < 5:
                candidate_id = candidate.get("candidate_id", "<unknown>")
                warning_notes.append(f"{candidate_id}: scoring failed with {exc.__class__.__name__}")
            continue

        scored_count += 1
        score_bands[scorecard.score_band] += 1
        scores.append(scorecard.static_fit_score)
        row = scorecard_to_flat_dict(scorecard)
        row["component_evidence"] = component_evidence_text(scorecard)
        debug_rows.append(row)
        for component in scorecard.components:
            component_raw_scores[component.name].append(component.raw_score)

        if scorecard.static_fit_score >= 0.70 and len(strong_examples) < top_n:
            strong_examples.append(row)
        if scorecard.static_fit_score < 0.35 and len(weak_examples) < top_n:
            weak_examples.append(row)

    top_rows = top_n_by_key(debug_rows, "static_fit_score", top_n, reverse=True)
    bottom_rows = top_n_by_key(debug_rows, "static_fit_score", top_n, reverse=False)
    component_averages = {
        name: round(mean(values), 4) for name, values in sorted(component_raw_scores.items())
    }

    return ScoreInspectionReport(
        total_seen=total_seen,
        scored_count=scored_count,
        scoring_error_count=scoring_error_count,
        score_band_counts=dict(score_bands),
        average_static_fit_score=round(mean(scores), 6) if scores else 0.0,
        top_debug_rows=top_rows,
        bottom_debug_rows=bottom_rows,
        component_averages=component_averages,
        strong_fit_examples=strong_examples[:top_n],
        weak_fit_examples=weak_examples[:top_n],
        warning_notes=warning_notes,
    )


def format_score_console_report(report: ScoreInspectionReport) -> str:
    lines = [
        "SignalRank AI Static Score Inspection",
        "=====================================",
        f"Total candidates seen: {report.total_seen}",
        f"Candidates scored: {report.scored_count}",
        f"Scoring errors or invalid records: {report.scoring_error_count}",
        f"Average static fit score: {report.average_static_fit_score:.4f}",
        "",
        "Score bands:",
        _format_dict(report.score_band_counts),
        "",
        "Component raw-score averages:",
        _format_float_dict(report.component_averages),
        "",
        "Top debug rows:",
        _format_rows(report.top_debug_rows),
        "",
        "Bottom debug rows:",
        _format_rows(report.bottom_debug_rows),
    ]
    if report.warning_notes:
        lines.extend(["", "Warnings:", *[f"- {note}" for note in report.warning_notes]])
    return "\n".join(lines)


def format_score_markdown_report(report: ScoreInspectionReport) -> str:
    lines = [
        "# Static Score Inspection Report",
        "",
        "## Summary",
        "",
        f"- Total candidates seen: {report.total_seen}",
        f"- Candidates scored: {report.scored_count}",
        f"- Scoring errors or invalid records: {report.scoring_error_count}",
        f"- Average static fit score: {report.average_static_fit_score:.4f}",
        "",
        "## Score Bands",
        _format_dict(report.score_band_counts),
        "",
        "## Component Raw-Score Averages",
        _format_float_dict(report.component_averages),
        "",
        "## Top Debug Rows",
        _format_rows(report.top_debug_rows),
        "",
        "## Bottom Debug Rows",
        _format_rows(report.bottom_debug_rows),
        "",
        "## Strong Fit Examples",
        _format_rows(report.strong_fit_examples),
        "",
        "## Weak Fit Examples",
        _format_rows(report.weak_fit_examples),
    ]
    if report.warning_notes:
        lines.extend(["", "## Warnings", *[f"- {note}" for note in report.warning_notes]])
    return "\n".join(lines) + "\n"


def score_rows_to_csv(rows: list[dict[str, Any]], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["candidate_id"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_dict(values: dict[str, int]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {key}: {value}" for key, value in sorted(values.items()))


def _format_float_dict(values: dict[str, float]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {key}: {value:.4f}" for key, value in sorted(values.items()))


def _format_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- None"
    lines = []
    for row in rows:
        lines.append(
            "- "
            f"{row.get('candidate_id')} | {row.get('static_fit_score'):.4f} | "
            f"{row.get('score_band')} | {row.get('short_summary')}"
        )
    return "\n".join(lines)
