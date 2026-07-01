from __future__ import annotations

import json

from src.sandbox_helpers import (
    cap_candidates_for_demo,
    load_demo_sample,
    parse_uploaded_candidate_file,
    run_demo_ranking,
    shorten_reasoning_for_table,
)


def test_load_demo_sample_returns_candidates():
    candidates = load_demo_sample()

    assert isinstance(candidates, list)
    assert candidates
    assert all("candidate_id" in candidate for candidate in candidates)


def test_cap_candidates_for_demo_caps_over_100_and_warns():
    candidates = [{"candidate_id": f"CAND_{index:07d}"} for index in range(105)]

    capped, warnings = cap_candidates_for_demo(candidates, max_candidates=100)

    assert len(capped) == 100
    assert warnings


def test_parse_uploaded_candidate_file_handles_json_bytes():
    payload = json.dumps(load_demo_sample()[:2]).encode("utf-8")

    candidates = parse_uploaded_candidate_file("sample.json", payload)

    assert len(candidates) == 2


def test_parse_uploaded_candidate_file_handles_jsonl_bytes():
    lines = "\n".join(json.dumps(candidate) for candidate in load_demo_sample()[:2])

    candidates = parse_uploaded_candidate_file("sample.jsonl", lines.encode("utf-8"))

    assert len(candidates) == 2


def test_run_demo_ranking_works_with_tiny_sample_top_k_3():
    result = run_demo_ranking(load_demo_sample()[:4], top_k=3, max_candidates=100)

    assert len(result.rows) == 3
    assert result.validation_text.startswith("Submission Validation Report")
    assert result.csv_bytes.startswith(b"candidate_id,rank,score,reasoning")
    assert result.xlsx_bytes.startswith(b"PK")
    assert "SignalRank AI Demo Report" in result.report_markdown


def test_run_demo_ranking_caps_top_k_above_available_count():
    candidates = load_demo_sample()[:8]
    result = run_demo_ranking(candidates, top_k=10, max_candidates=100)

    assert len(result.rows) == len(candidates)
    assert result.effective_top_k == len(candidates)
    assert any("Top K was capped" in warning for warning in result.warnings)
    assert "Selected Top K: 10" in result.report_markdown
    assert f"Effective Top K: {len(candidates)}" in result.report_markdown


def test_shorten_reasoning_for_table_shortens_long_text():
    text = "word " * 100

    shortened = shorten_reasoning_for_table(text, max_chars=40)

    assert len(shortened) <= 40
    assert shortened.endswith("...")
