from __future__ import annotations

import csv
import json

from src.combined_scoring import CombinedScorecard
from src.ranking import (
    RankedPreviewRow,
    format_ranking_console_report,
    rank_candidates_preview,
    write_ranking_preview_csv,
)
from tests.test_schema import make_candidate
from tests.test_scoring import make_keyword_stuffer, make_strong_candidate


def test_rank_candidates_preview_works_on_temp_json_file(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_keyword_stuffer(), make_strong_candidate()]), encoding="utf-8")

    result = rank_candidates_preview(path, top_k=2)

    assert result.total_seen == 2
    assert result.ranked_count == 2


def test_preview_ranks_start_at_one_and_are_sorted(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_keyword_stuffer(), make_strong_candidate()]), encoding="utf-8")

    result = rank_candidates_preview(path, top_k=2)

    assert result.rows[0].preview_rank == 1
    assert result.rows[0].final_score_preview >= result.rows[1].final_score_preview


def test_candidate_ids_are_unique_in_preview(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_keyword_stuffer(), make_strong_candidate()]), encoding="utf-8")

    result = rank_candidates_preview(path, top_k=2)
    ids = [row.candidate_id for row in result.rows]

    assert len(ids) == len(set(ids))


def test_deterministic_tie_break_by_candidate_id(monkeypatch, tmp_path):
    path = tmp_path / "candidates.json"
    first = make_candidate()
    second = make_candidate()
    first["candidate_id"] = "CAND_0000999"
    second["candidate_id"] = "CAND_0000002"
    path.write_text(json.dumps([first, second]), encoding="utf-8")

    def fake_scorecard(candidate: dict) -> CombinedScorecard:
        candidate_id = candidate["candidate_id"]
        return CombinedScorecard(
            candidate_id=candidate_id,
            static_fit_score=0.5,
            redrob_availability_score=0.5,
            behavior_multiplier=1.0,
            trap_total_penalty=0.0,
            trap_penalty_multiplier=1.0,
            score_before_caps=0.5,
            score_after_caps=0.5,
            final_score=0.5,
            final_score_band="borderline_fit",
            applied_caps=[],
            static_band="weak_static_fit",
            behavior_band="neutral_hireability",
            trap_severity_band="clean",
            title="Engineer",
            title_category="unknown",
            years_of_experience=5,
            location="Pune",
            location_category="preferred",
            key_flags={"has_real_retrieval_or_ranking_evidence": False},
            evidence_seeds=["title: Engineer"],
            debug_summary="fake",
        )

    monkeypatch.setattr("src.ranking.compute_combined_scorecard", fake_scorecard)

    result = rank_candidates_preview(path, top_k=2)

    assert [row.candidate_id for row in result.rows] == ["CAND_0000002", "CAND_0000999"]


def test_invalid_candidates_are_skipped_and_counted(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_candidate(), {"candidate_id": "BAD"}]), encoding="utf-8")

    result = rank_candidates_preview(path, top_k=5)

    assert result.total_seen == 2
    assert result.skipped_invalid_count == 1
    assert result.ranked_count == 1


def test_write_ranking_preview_csv_writes_expected_columns(tmp_path):
    out_path = tmp_path / "ranking_preview.csv"
    row = RankedPreviewRow(
        preview_rank=1,
        candidate_id="CAND_0000001",
        final_score_preview=0.8,
        final_score_band="strong_fit",
        title="Engineer",
        title_category="target",
        years_of_experience=6,
        location="Pune",
        location_category="preferred",
        static_fit_score=0.8,
        redrob_availability_score=0.8,
        behavior_multiplier=1.0,
        trap_total_penalty=0.0,
        trap_penalty_multiplier=1.0,
        applied_cap_codes="",
        debug_summary="debug",
        evidence_seeds=["seed"],
        flat_debug={"candidate_id": "CAND_0000001", "final_score_preview": 0.8},
    )

    write_ranking_preview_csv([row], out_path)

    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert "preview_rank" in (reader.fieldnames or [])
        assert "final_score_preview" in (reader.fieldnames or [])


def test_format_ranking_console_report_contains_title(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([make_strong_candidate()]), encoding="utf-8")

    result = rank_candidates_preview(path, top_k=1)

    assert "Ranking Preview" in format_ranking_console_report(result)
