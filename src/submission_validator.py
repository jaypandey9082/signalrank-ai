from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.reasoning_quality import is_too_generic
from src.submission import SubmissionRow, submission_rows_to_dicts


REQUIRED_SUBMISSION_COLUMNS = ["candidate_id", "rank", "score", "reasoning"]
CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")
INTERNAL_DEBUG_WORDS = (
    "final_score_preview",
    "guardrail",
    "scorecard",
    "score_band",
    "honeypot confirmed",
    "hidden ground truth",
)


@dataclass
class SubmissionValidationIssue:
    severity: str
    code: str
    message: str


@dataclass
class SubmissionValidationReport:
    is_valid: bool
    row_count: int
    error_count: int
    warning_count: int
    issues: list[SubmissionValidationIssue]


def validate_submission_rows(
    rows: list[SubmissionRow] | list[dict],
    expected_count: int = 100,
) -> SubmissionValidationReport:
    dict_rows = _coerce_rows(rows)
    issues: list[SubmissionValidationIssue] = []
    if len(dict_rows) != expected_count:
        issues.append(_issue("error", "row_count", f"Expected {expected_count} rows, found {len(dict_rows)}."))

    seen_ids: set[str] = set()
    seen_ranks: set[int] = set()
    score_by_rank: list[tuple[int, float, str]] = []
    reasoning_counts: dict[str, int] = {}

    for index, row in enumerate(dict_rows, start=1):
        missing = [column for column in REQUIRED_SUBMISSION_COLUMNS if column not in row]
        if missing:
            issues.append(_issue("error", "missing_columns", f"Row {index} missing columns: {missing}."))
            continue
        candidate_id = str(row.get("candidate_id", "")).strip()
        rank_value = row.get("rank")
        score_value = row.get("score")
        reasoning = str(row.get("reasoning", "")).strip()

        if not CANDIDATE_ID_PATTERN.match(candidate_id):
            issues.append(_issue("error", "invalid_candidate_id", f"Row {index} has invalid candidate_id {candidate_id!r}."))
        elif candidate_id in seen_ids:
            issues.append(_issue("error", "duplicate_candidate_id", f"Duplicate candidate_id {candidate_id}."))
        seen_ids.add(candidate_id)

        rank = _parse_int(rank_value)
        if rank is None:
            issues.append(_issue("error", "invalid_rank", f"Row {index} rank must be an integer."))
        elif rank in seen_ranks:
            issues.append(_issue("error", "duplicate_rank", f"Duplicate rank {rank}."))
        else:
            seen_ranks.add(rank)

        score = _parse_float(score_value)
        if score is None:
            issues.append(_issue("error", "invalid_score", f"Row {index} score must be numeric."))
        elif score < 0 or score > 1:
            issues.append(_issue("error", "score_out_of_range", f"Row {index} score must be between 0 and 1."))

        if rank is not None and score is not None:
            score_by_rank.append((rank, score, candidate_id))

        if not reasoning:
            issues.append(_issue("error", "empty_reasoning", f"Row {index} reasoning is empty."))
        if len(reasoning) > 500:
            issues.append(_issue("error", "reasoning_too_long", f"Row {index} reasoning exceeds 500 chars."))
        elif len(reasoning) > 450:
            issues.append(_issue("warning", "reasoning_long", f"Row {index} reasoning exceeds 450 chars."))
        if reasoning and is_too_generic(reasoning):
            issues.append(_issue("warning", "generic_reasoning", f"Row {index} reasoning looks generic."))
        if any(word in reasoning.lower() for word in INTERNAL_DEBUG_WORDS):
            issues.append(_issue("error", "debug_word_in_reasoning", f"Row {index} reasoning contains internal debug wording."))
        if reasoning:
            reasoning_counts[reasoning] = reasoning_counts.get(reasoning, 0) + 1

    expected_ranks = set(range(1, expected_count + 1))
    if seen_ranks != expected_ranks:
        missing = sorted(expected_ranks - seen_ranks)
        extra = sorted(seen_ranks - expected_ranks)
        issues.append(_issue("error", "rank_sequence", f"Ranks must be exactly 1..{expected_count}; missing={missing}, extra={extra}."))

    score_by_rank.sort(key=lambda item: item[0])
    for current, nxt in zip(score_by_rank, score_by_rank[1:]):
        rank_a, score_a, candidate_a = current
        rank_b, score_b, candidate_b = nxt
        if score_a < score_b:
            issues.append(_issue("error", "score_increasing", f"Score increases from rank {rank_a} to {rank_b}."))
        if score_a == score_b and candidate_a > candidate_b:
            issues.append(_issue("error", "tie_break", f"Equal score tie at ranks {rank_a}/{rank_b} violates candidate_id ascending."))

    if score_by_rank and len({score for _, score, _ in score_by_rank}) == 1:
        issues.append(_issue("warning", "all_scores_identical", "All submission scores are identical."))
    repeated = [reason for reason, count in reasoning_counts.items() if count > 1]
    if repeated:
        issues.append(_issue("warning", "repeated_reasoning", f"{len(repeated)} repeated reasoning text(s) found."))

    errors = sum(1 for issue in issues if issue.severity == "error")
    warnings = sum(1 for issue in issues if issue.severity == "warning")
    return SubmissionValidationReport(
        is_valid=errors == 0,
        row_count=len(dict_rows),
        error_count=errors,
        warning_count=warnings,
        issues=issues,
    )


def validate_submission_file(csv_path: str | Path, expected_count: int = 100) -> SubmissionValidationReport:
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        return validate_submission_rows(list(csv.DictReader(handle)), expected_count=expected_count)


def format_submission_validation_report(report: SubmissionValidationReport) -> str:
    lines = [
        "Submission Validation Report",
        "============================",
        f"Valid: {report.is_valid}",
        f"Rows: {report.row_count}",
        f"Errors: {report.error_count}",
        f"Warnings: {report.warning_count}",
    ]
    lines.extend(f"- [{issue.severity}] {issue.code}: {issue.message}" for issue in report.issues)
    return "\n".join(lines)


def format_submission_validation_markdown(report: SubmissionValidationReport) -> str:
    lines = [
        "# Submission Validation Report",
        "",
        f"- Valid: {report.is_valid}",
        f"- Rows: {report.row_count}",
        f"- Errors: {report.error_count}",
        f"- Warnings: {report.warning_count}",
    ]
    if report.issues:
        lines.extend(["", "## Issues"])
        lines.extend(f"- `{issue.severity}` `{issue.code}`: {issue.message}" for issue in report.issues)
    return "\n".join(lines) + "\n"


def _coerce_rows(rows: list[SubmissionRow] | list[dict]) -> list[dict[str, Any]]:
    if not rows:
        return []
    if isinstance(rows[0], SubmissionRow):
        return submission_rows_to_dicts(rows)  # type: ignore[arg-type]
    return [dict(row) for row in rows]  # type: ignore[arg-type]


def _parse_int(value: object) -> int | None:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if str(parsed) == str(value).strip() else None


def _parse_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _issue(severity: str, code: str, message: str) -> SubmissionValidationIssue:
    return SubmissionValidationIssue(severity=severity, code=code, message=message)
