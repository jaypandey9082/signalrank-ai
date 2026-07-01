from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

from src.load_data import iter_candidates
from src.redrob_scoring import (
    apply_behavior_multiplier_preview,
    compute_redrob_scorecard,
    redrob_scorecard_to_flat_dict,
)
from src.schema import validate_candidate
from src.scoring import score_candidate
from src.utils import bool_rate, ensure_parent_dir, safe_mean, top_n_by_key


@dataclass
class RedrobInspectionReport:
    total_seen: int
    scored_count: int
    scoring_error_count: int
    average_redrob_availability_score: float
    average_behavior_multiplier: float
    behavior_band_counts: dict[str, int]
    risk_flag_counts: dict[str, int]
    component_averages: dict[str, float]
    raw_signal_summary: dict[str, object]
    high_hireability_examples: list[dict[str, Any]]
    risky_hireability_examples: list[dict[str, Any]]
    preview_static_behavior_examples: list[dict[str, Any]]


def inspect_redrob_scores(
    path: str | Path,
    limit: int | None = None,
    top_n: int = 20,
    as_of_date: str | date | None = None,
    include_static_preview: bool = False,
) -> RedrobInspectionReport:
    total_seen = 0
    scored_count = 0
    scoring_error_count = 0
    behavior_bands: Counter[str] = Counter()
    risk_flags: Counter[str] = Counter()
    component_raw_scores: dict[str, list[float]] = defaultdict(list)
    redrob_scores: list[float] = []
    multipliers: list[float] = []
    rows: list[dict[str, Any]] = []
    preview_rows: list[dict[str, Any]] = []

    open_to_work_values: list[bool] = []
    willing_values: list[bool] = []
    recruiter_response_rates: list[float] = []
    notice_periods: list[float] = []
    response_times: list[float] = []
    verified_email_values: list[bool] = []
    verified_phone_values: list[bool] = []
    linkedin_values: list[bool] = []

    for candidate in iter_candidates(path):
        if limit is not None and total_seen >= limit:
            break
        total_seen += 1

        validation = validate_candidate(candidate)
        if not validation.is_valid:
            scoring_error_count += 1
            continue

        try:
            scorecard = compute_redrob_scorecard(candidate, as_of_date=as_of_date)
        except (TypeError, ValueError, KeyError, AttributeError):
            scoring_error_count += 1
            continue

        scored_count += 1
        row = redrob_scorecard_to_flat_dict(scorecard)
        rows.append(row)
        behavior_bands[scorecard.behavior_band] += 1
        redrob_scores.append(scorecard.redrob_availability_score)
        multipliers.append(scorecard.behavior_multiplier)
        for flag_name, flag_value in scorecard.risk_flags.items():
            if flag_value:
                risk_flags[flag_name] += 1
        for component in scorecard.components:
            component_raw_scores[component.name].append(component.raw_score)

        _collect_raw_signal_values(
            scorecard.raw_snapshot,
            open_to_work_values,
            willing_values,
            recruiter_response_rates,
            notice_periods,
            response_times,
            verified_email_values,
            verified_phone_values,
            linkedin_values,
        )

        if include_static_preview and len(preview_rows) < top_n:
            static_scorecard = score_candidate(candidate)
            preview_rows.append(
                {
                    "candidate_id": scorecard.candidate_id,
                    "static_fit_score": static_scorecard.static_fit_score,
                    "redrob_availability_score": scorecard.redrob_availability_score,
                    "behavior_multiplier": scorecard.behavior_multiplier,
                    "preview_static_behavior_score": apply_behavior_multiplier_preview(
                        static_scorecard.static_fit_score,
                        scorecard,
                    ),
                    "note": "preview only; not final score",
                }
            )

    high_examples = top_n_by_key(rows, "redrob_availability_score", top_n, reverse=True)
    risky_examples = top_n_by_key(rows, "redrob_availability_score", top_n, reverse=False)
    component_averages = {
        name: round(mean(values), 4) for name, values in sorted(component_raw_scores.items())
    }
    return RedrobInspectionReport(
        total_seen=total_seen,
        scored_count=scored_count,
        scoring_error_count=scoring_error_count,
        average_redrob_availability_score=round(safe_mean(redrob_scores), 6),
        average_behavior_multiplier=round(safe_mean(multipliers), 6),
        behavior_band_counts=dict(behavior_bands),
        risk_flag_counts=dict(risk_flags),
        component_averages=component_averages,
        raw_signal_summary={
            "open_to_work_rate": round(bool_rate(open_to_work_values), 4),
            "willing_to_relocate_rate": round(bool_rate(willing_values), 4),
            "avg_recruiter_response_rate": round(safe_mean(recruiter_response_rates), 4),
            "avg_notice_period_days": round(safe_mean(notice_periods), 2),
            "avg_response_time_hours": round(safe_mean(response_times), 2),
            "verified_email_rate": round(bool_rate(verified_email_values), 4),
            "verified_phone_rate": round(bool_rate(verified_phone_values), 4),
            "linkedin_connected_rate": round(bool_rate(linkedin_values), 4),
        },
        high_hireability_examples=high_examples,
        risky_hireability_examples=risky_examples,
        preview_static_behavior_examples=preview_rows,
    )


def format_redrob_console_report(report: RedrobInspectionReport) -> str:
    lines = [
        "SignalRank AI Redrob Behavior Inspection",
        "=========================================",
        f"Total candidates seen: {report.total_seen}",
        f"Candidates scored: {report.scored_count}",
        f"Scoring errors or invalid records: {report.scoring_error_count}",
        f"Average Redrob availability score: {report.average_redrob_availability_score:.4f}",
        f"Average behavior multiplier: {report.average_behavior_multiplier:.4f}",
        "",
        "Behavior bands:",
        _format_dict(report.behavior_band_counts),
        "",
        "Risk flags:",
        _format_dict(report.risk_flag_counts),
        "",
        "Component raw-score averages:",
        _format_float_dict(report.component_averages),
        "",
        "Raw signal summary:",
        _format_object_dict(report.raw_signal_summary),
        "",
        "High hireability examples:",
        _format_rows(report.high_hireability_examples),
        "",
        "Risky hireability examples:",
        _format_rows(report.risky_hireability_examples),
    ]
    if report.preview_static_behavior_examples:
        lines.extend(
            [
                "",
                "Static x behavior preview examples (not final score):",
                _format_preview_rows(report.preview_static_behavior_examples),
            ]
        )
    return "\n".join(lines)


def format_redrob_markdown_report(report: RedrobInspectionReport) -> str:
    lines = [
        "# Redrob Behavior Inspection Report",
        "",
        "## Summary",
        "",
        f"- Total candidates seen: {report.total_seen}",
        f"- Candidates scored: {report.scored_count}",
        f"- Scoring errors or invalid records: {report.scoring_error_count}",
        f"- Average Redrob availability score: {report.average_redrob_availability_score:.4f}",
        f"- Average behavior multiplier: {report.average_behavior_multiplier:.4f}",
        "",
        "## Behavior Bands",
        _format_dict(report.behavior_band_counts),
        "",
        "## Risk Flags",
        _format_dict(report.risk_flag_counts),
        "",
        "## Component Raw-Score Averages",
        _format_float_dict(report.component_averages),
        "",
        "## Raw Signal Summary",
        _format_object_dict(report.raw_signal_summary),
        "",
        "## High Hireability Examples",
        _format_rows(report.high_hireability_examples),
        "",
        "## Risky Hireability Examples",
        _format_rows(report.risky_hireability_examples),
    ]
    if report.preview_static_behavior_examples:
        lines.extend(
            [
                "",
                "## Static x Behavior Preview Examples",
                "",
                "These rows are preview-only and are not final ranking scores.",
                "",
                _format_preview_rows(report.preview_static_behavior_examples),
            ]
        )
    return "\n".join(lines) + "\n"


def redrob_rows_to_csv(rows: list[dict[str, Any]], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["candidate_id"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _collect_raw_signal_values(
    snapshot: dict[str, object],
    open_to_work_values: list[bool],
    willing_values: list[bool],
    recruiter_response_rates: list[float],
    notice_periods: list[float],
    response_times: list[float],
    verified_email_values: list[bool],
    verified_phone_values: list[bool],
    linkedin_values: list[bool],
) -> None:
    _append_bool(open_to_work_values, snapshot.get("open_to_work_flag"))
    _append_bool(willing_values, snapshot.get("willing_to_relocate"))
    _append_number(recruiter_response_rates, snapshot.get("recruiter_response_rate"))
    _append_number(notice_periods, snapshot.get("notice_period_days"))
    _append_number(response_times, snapshot.get("avg_response_time_hours"))
    _append_bool(verified_email_values, snapshot.get("verified_email"))
    _append_bool(verified_phone_values, snapshot.get("verified_phone"))
    _append_bool(linkedin_values, snapshot.get("linkedin_connected"))


def _append_number(values: list[float], value: object) -> None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        values.append(float(value))


def _append_bool(values: list[bool], value: object) -> None:
    if isinstance(value, bool):
        values.append(value)


def _format_dict(values: dict[str, int]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {key}: {value}" for key, value in sorted(values.items()))


def _format_float_dict(values: dict[str, float]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {key}: {value:.4f}" for key, value in sorted(values.items()))


def _format_object_dict(values: dict[str, object]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {key}: {value}" for key, value in sorted(values.items()))


def _format_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- None"
    return "\n".join(
        "- "
        f"{row.get('candidate_id')} | {row.get('redrob_availability_score'):.4f} | "
        f"{row.get('behavior_band')} | x{row.get('behavior_multiplier'):.2f} | "
        f"{row.get('short_summary')}"
        for row in rows
    )


def _format_preview_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- None"
    return "\n".join(
        "- "
        f"{row.get('candidate_id')} | static={row.get('static_fit_score'):.4f} | "
        f"multiplier={row.get('behavior_multiplier'):.2f} | "
        f"preview={row.get('preview_static_behavior_score'):.4f}"
        for row in rows
    )
