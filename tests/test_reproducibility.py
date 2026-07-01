from __future__ import annotations

import csv

import pytest

from src.reproducibility import assert_deterministic_outputs, compare_csv_files, file_sha256, rows_sha256


def test_file_sha256_returns_stable_hash(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("hello", encoding="utf-8")

    assert file_sha256(path) == file_sha256(path)


def test_compare_csv_files_detects_identical_files(tmp_path):
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    _write_csv(first, [["CAND_0000001", "1", "0.9", "Good evidence."]])
    _write_csv(second, [["CAND_0000001", "1", "0.9", "Good evidence."]])

    comparison = compare_csv_files(first, second)

    assert comparison["same_hash"]
    assert comparison["row_count_a"] == 1


def test_compare_csv_files_detects_changed_file(tmp_path):
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    _write_csv(first, [["CAND_0000001", "1", "0.9", "Good evidence."]])
    _write_csv(second, [["CAND_0000002", "1", "0.9", "Good evidence."]])

    comparison = compare_csv_files(first, second)

    assert not comparison["same_hash"]
    assert "first difference" in comparison["first_difference_summary"]


def test_rows_sha256_is_deterministic():
    rows = [{"rank": 1, "candidate_id": "CAND_0000001", "score": 0.9}]

    assert rows_sha256(rows) == rows_sha256(rows)


def test_assert_deterministic_outputs_raises_on_difference(tmp_path):
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    _write_csv(first, [["CAND_0000001", "1", "0.9", "Good evidence."]])
    _write_csv(second, [["CAND_0000002", "1", "0.9", "Good evidence."]])

    with pytest.raises(AssertionError):
        assert_deterministic_outputs(first, second)


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        writer.writerows(rows)
