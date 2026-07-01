from __future__ import annotations

import json

from src.inspect import format_markdown_report, inspect_candidates
from tests.test_schema import make_candidate


def test_inspect_candidates_returns_total_seen_for_tiny_sample(tmp_path):
    path = tmp_path / "candidates.json"
    candidates = [make_candidate(), _candidate("CAND_0000002", "Data Engineer")]
    path.write_text(json.dumps(candidates), encoding="utf-8")

    report = inspect_candidates(path)

    assert report.total_seen == 2
    assert report.valid_count == 2


def test_top_skills_are_counted(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate(), _candidate("CAND_0000002", "Data Engineer")]), encoding="utf-8")

    report = inspect_candidates(path)

    assert ("Python", 2) in report.top_skills


def test_experience_summary_has_expected_keys(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate()]), encoding="utf-8")

    report = inspect_candidates(path)

    assert {"min", "max", "average", "median", "count", "bands"} <= set(
        report.experience_summary
    )


def test_markdown_report_contains_title(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate()]), encoding="utf-8")

    report = inspect_candidates(path)
    markdown = format_markdown_report(report)

    assert "Dataset Inspection Report" in markdown


def test_strict_mode_marks_range_problem_invalid(tmp_path):
    candidate = make_candidate()
    candidate["redrob_signals"]["recruiter_response_rate"] = 2.0
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([candidate]), encoding="utf-8")

    report = inspect_candidates(path, strict=True)

    assert report.invalid_count == 1


def _candidate(candidate_id: str, title: str) -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = candidate_id
    candidate["profile"]["current_title"] = title
    return candidate
