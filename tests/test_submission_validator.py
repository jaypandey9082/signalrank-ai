from __future__ import annotations

from src.export import write_submission_csv
from src.submission import SubmissionRow
from src.submission_validator import validate_submission_file, validate_submission_rows


def valid_rows() -> list[SubmissionRow]:
    return [
        SubmissionRow("CAND_0000001", 1, 0.9, "6 years with production ranking/search evidence."),
        SubmissionRow("CAND_0000002", 2, 0.8, "5 years with retrieval and evaluation evidence."),
        SubmissionRow("CAND_0000003", 3, 0.7, "Pune engineer with production ML evidence."),
    ]


def test_valid_rows_pass():
    report = validate_submission_rows(valid_rows(), expected_count=3)

    assert report.is_valid


def test_missing_row_count_fails():
    report = validate_submission_rows(valid_rows()[:2], expected_count=3)

    assert not report.is_valid
    assert any(issue.code == "row_count" for issue in report.issues)


def test_duplicate_candidate_id_fails():
    rows = valid_rows()
    rows[1].candidate_id = rows[0].candidate_id

    report = validate_submission_rows(rows, expected_count=3)

    assert any(issue.code == "duplicate_candidate_id" for issue in report.issues)


def test_duplicate_rank_fails():
    rows = valid_rows()
    rows[1].rank = 1

    report = validate_submission_rows(rows, expected_count=3)

    assert any(issue.code == "duplicate_rank" for issue in report.issues)


def test_missing_rank_fails():
    rows = [{"candidate_id": "CAND_0000001", "score": 0.9, "reasoning": "ranking/search evidence"}]

    report = validate_submission_rows(rows, expected_count=1)

    assert any(issue.code == "missing_columns" for issue in report.issues)


def test_score_increasing_fails():
    rows = valid_rows()
    rows[1].score = 0.95

    report = validate_submission_rows(rows, expected_count=3)

    assert any(issue.code == "score_increasing" for issue in report.issues)


def test_empty_reasoning_fails():
    rows = valid_rows()
    rows[0].reasoning = ""

    report = validate_submission_rows(rows, expected_count=3)

    assert any(issue.code == "empty_reasoning" for issue in report.issues)


def test_generic_reasoning_warns():
    rows = valid_rows()
    rows[0].reasoning = "Good fit for the role."

    report = validate_submission_rows(rows, expected_count=3)

    assert any(issue.code == "generic_reasoning" and issue.severity == "warning" for issue in report.issues)


def test_invalid_candidate_id_fails():
    rows = valid_rows()
    rows[0].candidate_id = "BAD"

    report = validate_submission_rows(rows, expected_count=3)

    assert any(issue.code == "invalid_candidate_id" for issue in report.issues)


def test_repeated_identical_reasoning_warns():
    rows = valid_rows()
    rows[1].reasoning = rows[0].reasoning

    report = validate_submission_rows(rows, expected_count=3)

    assert any(issue.code == "repeated_reasoning" for issue in report.issues)


def test_validate_submission_file_reads_csv(tmp_path):
    path = tmp_path / "submission.csv"
    rows = valid_rows()
    write_submission_csv(rows, path)

    report = validate_submission_file(path, expected_count=3)

    assert report.is_valid
