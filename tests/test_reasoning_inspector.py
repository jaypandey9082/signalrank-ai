from __future__ import annotations

import csv
import json

from src.reasoning_inspector import (
    build_reasoning_preview,
    format_reasoning_markdown_report,
    write_reasoning_preview_csv,
)
from tests.test_schema import make_candidate
from tests.test_scoring import make_keyword_stuffer, make_strong_candidate


def test_build_reasoning_preview_works_on_temp_json_file(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate(), make_keyword_stuffer()]), encoding="utf-8")

    report = build_reasoning_preview(path, top_k=2)

    assert report.total_seen == 2
    assert report.ranked_count == 2


def test_reasoned_count_matches_ranked_count(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate(), make_keyword_stuffer()]), encoding="utf-8")

    report = build_reasoning_preview(path, top_k=2)

    assert report.reasoned_count == report.ranked_count


def test_preview_rows_include_reasoning_preview(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate()]), encoding="utf-8")

    report = build_reasoning_preview(path, top_k=1)

    assert report.preview_rows[0]["reasoning_preview"]


def test_markdown_report_contains_title(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate()]), encoding="utf-8")

    report = build_reasoning_preview(path, top_k=1)

    assert "Reasoning Preview Report" in format_reasoning_markdown_report(report)


def test_debug_csv_writer_creates_expected_columns(tmp_path):
    out_path = tmp_path / "reasoning_preview.csv"
    write_reasoning_preview_csv(
        [{"candidate_id": "CAND_0000001", "reasoning_preview": "Reasoning text."}],
        out_path,
    )

    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert "candidate_id" in (reader.fieldnames or [])
        assert "reasoning_preview" in (reader.fieldnames or [])


def test_quality_report_is_included(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate()]), encoding="utf-8")

    report = build_reasoning_preview(path, top_k=1)

    assert report.quality_report.total_checked == 1


def test_invalid_candidate_is_skipped_without_crashing_reasoning(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate(), {"candidate_id": "BAD"}]), encoding="utf-8")

    report = build_reasoning_preview(path, top_k=5)

    assert report.total_seen == 2
    assert report.ranked_count == 1
