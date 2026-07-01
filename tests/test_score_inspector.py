from __future__ import annotations

import csv
import json

from src.score_inspector import (
    format_score_markdown_report,
    inspect_scores,
    score_rows_to_csv,
)
from tests.test_schema import make_candidate


def test_inspect_scores_works_on_temp_json(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate(), _candidate("CAND_0000002")]), encoding="utf-8")

    report = inspect_scores(path)

    assert report.total_seen == 2
    assert report.scored_count == 2


def test_score_band_counts_exists(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate()]), encoding="utf-8")

    report = inspect_scores(path)

    assert report.score_band_counts


def test_markdown_report_contains_title(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate()]), encoding="utf-8")

    report = inspect_scores(path)

    assert "Static Score Inspection Report" in format_score_markdown_report(report)


def test_debug_csv_writer_creates_expected_columns(tmp_path):
    out_path = tmp_path / "debug_static_scores.csv"
    score_rows_to_csv(
        [{"candidate_id": "CAND_0000001", "static_fit_score": 0.8}],
        out_path,
    )

    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert "candidate_id" in (reader.fieldnames or [])
        assert "static_fit_score" in (reader.fieldnames or [])


def test_inspect_scores_continues_when_one_candidate_invalid(tmp_path):
    path = tmp_path / "candidates.json"
    invalid = {"candidate_id": "BAD"}
    path.write_text(json.dumps([make_candidate(), invalid]), encoding="utf-8")

    report = inspect_scores(path)

    assert report.total_seen == 2
    assert report.scored_count == 1
    assert report.scoring_error_count == 1


def _candidate(candidate_id: str) -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = candidate_id
    return candidate
