from __future__ import annotations

import json

import pytest

from src.submission import build_submission_rows, submission_rows_to_dicts
from tests.test_scoring import make_keyword_stuffer, make_strong_candidate


def test_build_submission_rows_works_with_partial_top_k(tmp_path):
    path = tmp_path / "candidates.json"
    first = make_strong_candidate()
    second = make_keyword_stuffer()
    third = make_strong_candidate()
    third["candidate_id"] = "CAND_0000103"
    path.write_text(json.dumps([first, second, third]), encoding="utf-8")

    result = build_submission_rows(path, top_k=3, allow_partial=True)

    assert result.submitted_count == 3
    assert [row.rank for row in result.rows] == [1, 2, 3]


def test_submission_scores_are_non_increasing_and_ids_unique(tmp_path):
    path = tmp_path / "candidates.json"
    candidates = [make_strong_candidate(), make_keyword_stuffer()]
    candidates[1]["candidate_id"] = "CAND_0000111"
    path.write_text(json.dumps(candidates), encoding="utf-8")

    result = build_submission_rows(path, top_k=2, allow_partial=True)
    scores = [row.score for row in result.rows]
    ids = [row.candidate_id for row in result.rows]

    assert scores == sorted(scores, reverse=True)
    assert len(ids) == len(set(ids))
    assert all(row.reasoning for row in result.rows)


def test_top_k_not_100_without_allow_partial_raises(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate()]), encoding="utf-8")

    with pytest.raises(ValueError):
        build_submission_rows(path, top_k=1)


def test_limit_without_allow_partial_raises(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate()]), encoding="utf-8")

    with pytest.raises(ValueError):
        build_submission_rows(path, limit=1)


def test_fewer_than_top_k_raises_even_with_allow_partial(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate()]), encoding="utf-8")

    with pytest.raises(ValueError, match="Could only produce 1 rows; expected 2"):
        build_submission_rows(path, top_k=2, allow_partial=True)


def test_submission_rows_to_dicts_returns_exact_key_order(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate()]), encoding="utf-8")

    result = build_submission_rows(path, top_k=1, allow_partial=True)
    row = submission_rows_to_dicts(result.rows)[0]

    assert list(row.keys()) == ["candidate_id", "rank", "score", "reasoning"]


def test_strong_candidate_ranks_above_wrong_role_keyword_stuffer(tmp_path):
    path = tmp_path / "candidates.json"
    strong = make_strong_candidate()
    weak = make_keyword_stuffer()
    weak["candidate_id"] = "CAND_0000112"
    path.write_text(json.dumps([weak, strong]), encoding="utf-8")

    result = build_submission_rows(path, top_k=2, allow_partial=True)

    assert result.rows[0].candidate_id == strong["candidate_id"]
