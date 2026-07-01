from __future__ import annotations

from src.runtime_report import build_runtime_report, runtime_report_to_markdown, write_runtime_report
from src.submission import SubmissionBuildResult, SubmissionRow
from src.submission_validator import validate_submission_rows


def build_result() -> SubmissionBuildResult:
    rows = [
        SubmissionRow("CAND_0000001", 1, 0.9, "6 years with production ranking/search evidence."),
    ]
    return SubmissionBuildResult(
        total_seen=1,
        valid_count=1,
        ranked_count=1,
        submitted_count=1,
        skipped_invalid_count=0,
        scoring_error_count=0,
        elapsed_seconds=0.1,
        rows=rows,
        ranking_quality_summary="Ranking quality checks passed.",
        reasoning_quality_summary="Reasoning quality checks passed.",
        warnings=[],
        debug_rows=[{"rank": 1, "candidate_id": "CAND_0000001", "score": 0.9, "reasoning": rows[0].reasoning}],
    )


def test_build_runtime_report_returns_object():
    result = build_result()
    validation = validate_submission_rows(result.rows, expected_count=1)

    report = build_runtime_report(result, "candidates.jsonl", "submission.csv", "submission.xlsx", validation)

    assert report.submitted_count == 1


def test_runtime_report_to_markdown_contains_title_and_top_rows():
    result = build_result()
    validation = validate_submission_rows(result.rows, expected_count=1)
    report = build_runtime_report(result, "candidates.jsonl", "submission.csv", None, validation)
    markdown = runtime_report_to_markdown(report)

    assert "Submission Run Report" in markdown
    assert "CAND_0000001" in markdown


def test_write_runtime_report_creates_file(tmp_path):
    result = build_result()
    validation = validate_submission_rows(result.rows, expected_count=1)
    report = build_runtime_report(result, "candidates.jsonl", "submission.csv", None, validation)
    path = tmp_path / "report.md"

    write_runtime_report(report, path)

    assert path.exists()
