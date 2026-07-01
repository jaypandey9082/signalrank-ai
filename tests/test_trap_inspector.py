from __future__ import annotations

import csv
import json

from src.trap_inspector import (
    format_trap_markdown_report,
    inspect_traps,
    trap_rows_to_csv,
)
from tests.test_schema import make_candidate
from tests.test_trap_penalties import strong_candidate, wrong_role_keyword_candidate


def test_inspect_traps_works_on_temp_json(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(
        json.dumps([strong_candidate(), wrong_role_keyword_candidate()]),
        encoding="utf-8",
    )

    report = inspect_traps(path)

    assert report.total_seen == 2
    assert report.scored_count == 2
    assert report.severity_band_counts


def test_trap_report_contains_title(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([strong_candidate()]), encoding="utf-8")

    report = inspect_traps(path)

    assert "Trap Inspection Report" in format_trap_markdown_report(report)


def test_trap_debug_csv_writer_creates_expected_columns(tmp_path):
    out_path = tmp_path / "debug_traps.csv"
    trap_rows_to_csv(
        [{"candidate_id": "CAND_0000001", "total_penalty": 0.2}],
        out_path,
    )

    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert "candidate_id" in (reader.fieldnames or [])
        assert "total_penalty" in (reader.fieldnames or [])


def test_include_preview_does_not_crash(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([strong_candidate()]), encoding="utf-8")

    report = inspect_traps(path, include_preview=True)

    assert report.preview_rows
    assert report.preview_rows[0]["note"] == "preview only; not final ranking"


def test_inspector_continues_when_one_candidate_invalid(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate(), {"candidate_id": "BAD"}]), encoding="utf-8")

    report = inspect_traps(path)

    assert report.total_seen == 2
    assert report.scored_count == 1
    assert report.scoring_error_count == 1
