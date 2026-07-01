from __future__ import annotations

import csv
import zipfile

from src.export import read_submission_csv, write_debug_csv, write_submission_csv, write_submission_xlsx
from src.submission import SubmissionRow


def rows() -> list[SubmissionRow]:
    return [
        SubmissionRow("CAND_0000001", 1, 0.9, "6 years with production ranking/search evidence."),
        SubmissionRow("CAND_0000002", 2, 0.8, "5 years with retrieval and evaluation evidence."),
    ]


def test_write_submission_csv_creates_file_with_exact_columns(tmp_path):
    path = tmp_path / "submission.csv"
    write_submission_csv(rows(), path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        assert next(reader) == ["candidate_id", "rank", "score", "reasoning"]


def test_read_submission_csv_returns_rows(tmp_path):
    path = tmp_path / "submission.csv"
    write_submission_csv(rows(), path)

    loaded = read_submission_csv(path)

    assert len(loaded) == 2


def test_write_submission_xlsx_creates_file(tmp_path):
    path = tmp_path / "submission.xlsx"
    write_submission_xlsx(rows(), path)

    assert path.exists()
    with zipfile.ZipFile(path) as archive:
        assert "xl/worksheets/sheet1.xml" in archive.namelist()
        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert sheet.count("<row ") == 3
        assert "candidate_id" in sheet


def test_write_debug_csv_creates_debug_file(tmp_path):
    path = tmp_path / "debug_submission.csv"
    write_debug_csv([{"candidate_id": "CAND_0000001", "score": 0.9, "extra": "x"}], path)

    assert path.exists()
