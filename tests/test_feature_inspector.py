from __future__ import annotations

import csv
import json

from src.feature_inspector import (
    feature_rows_to_csv,
    format_feature_markdown_report,
    inspect_features,
)
from tests.test_schema import make_candidate


def test_inspect_features_works_on_temporary_json_file(tmp_path):
    path = tmp_path / "candidates.json"
    candidates = [make_candidate(), _candidate("CAND_0000002", "Marketing Manager")]
    path.write_text(json.dumps(candidates), encoding="utf-8")

    report = inspect_features(path)

    assert report.total_seen == 2
    assert report.extracted_count == 2


def test_report_has_title_category_counts(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate()]), encoding="utf-8")

    report = inspect_features(path)

    assert report.title_category_counts["target"] == 1


def test_markdown_report_contains_title(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate()]), encoding="utf-8")

    report = inspect_features(path)

    assert "Feature Inspection Report" in format_feature_markdown_report(report)


def test_debug_csv_writer_creates_candidate_id_column(tmp_path):
    out_path = tmp_path / "debug_features.csv"
    feature_rows_to_csv([{"candidate_id": "CAND_0000001", "title_category": "target"}], out_path)

    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert "candidate_id" in (reader.fieldnames or [])


def _candidate(candidate_id: str, title: str) -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = candidate_id
    candidate["profile"]["current_title"] = title
    return candidate
