from __future__ import annotations

import csv
import json

from src.redrob_inspector import (
    format_redrob_markdown_report,
    inspect_redrob_scores,
    redrob_rows_to_csv,
)
from tests.test_redrob_scoring import good_behavior_candidate, poor_behavior_candidate
from tests.test_schema import make_candidate


def test_inspect_redrob_scores_works_on_temp_json(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(
        json.dumps([good_behavior_candidate(), poor_behavior_candidate()]),
        encoding="utf-8",
    )

    report = inspect_redrob_scores(path)

    assert report.total_seen == 2
    assert report.scored_count == 2


def test_behavior_band_counts_exists(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([good_behavior_candidate()]), encoding="utf-8")

    report = inspect_redrob_scores(path)

    assert report.behavior_band_counts


def test_risk_flag_counts_exists(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([poor_behavior_candidate()]), encoding="utf-8")

    report = inspect_redrob_scores(path)

    assert report.risk_flag_counts


def test_markdown_report_contains_title(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([good_behavior_candidate()]), encoding="utf-8")

    report = inspect_redrob_scores(path)

    assert "Redrob Behavior Inspection Report" in format_redrob_markdown_report(report)


def test_debug_csv_writer_creates_expected_columns(tmp_path):
    out_path = tmp_path / "debug_redrob.csv"
    redrob_rows_to_csv(
        [{"candidate_id": "CAND_0000001", "redrob_availability_score": 0.8}],
        out_path,
    )

    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert "candidate_id" in (reader.fieldnames or [])
        assert "redrob_availability_score" in (reader.fieldnames or [])


def test_include_static_preview_does_not_crash(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([good_behavior_candidate()]), encoding="utf-8")

    report = inspect_redrob_scores(path, include_static_preview=True)

    assert report.preview_static_behavior_examples


def test_inspector_continues_when_one_candidate_invalid(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate(), {"candidate_id": "BAD"}]), encoding="utf-8")

    report = inspect_redrob_scores(path)

    assert report.total_seen == 2
    assert report.scored_count == 1
    assert report.scoring_error_count == 1
