from __future__ import annotations

import gzip
import json

import pytest

from src.load_data import CandidateDataError, load_candidates
from src.normalize import join_candidate_text


def test_load_candidates_from_json_list(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text(
        json.dumps(
            [
                {"candidate_id": "CAND_0000001", "profile": {"current_title": "ML Engineer"}},
                {"candidate_id": "CAND_0000002", "profile": {"current_title": "Backend Engineer"}},
            ]
        ),
        encoding="utf-8",
    )

    candidates = load_candidates(path)

    assert len(candidates) == 2
    assert candidates[0]["candidate_id"] == "CAND_0000001"


def test_load_candidates_from_single_json_object(tmp_path):
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps({"candidate_id": "CAND_0000001"}), encoding="utf-8")

    candidates = load_candidates(path)

    assert candidates == [{"candidate_id": "CAND_0000001"}]


def test_load_candidates_from_jsonl(tmp_path):
    path = tmp_path / "candidates.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"candidate_id": "CAND_0000001"}),
                "",
                json.dumps({"candidate_id": "CAND_0000002"}),
            ]
        ),
        encoding="utf-8",
    )

    candidates = load_candidates(path)

    assert [candidate["candidate_id"] for candidate in candidates] == [
        "CAND_0000001",
        "CAND_0000002",
    ]


def test_load_candidates_from_jsonl_gz(tmp_path):
    path = tmp_path / "candidates.jsonl.gz"
    rows = [
        json.dumps({"candidate_id": "CAND_0000001"}),
        json.dumps({"candidate_id": "CAND_0000002"}),
    ]
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(rows))

    candidates = load_candidates(path)

    assert len(candidates) == 2
    assert candidates[1]["candidate_id"] == "CAND_0000002"


def test_load_candidates_limit(tmp_path):
    path = tmp_path / "candidates.jsonl"
    path.write_text(
        "\n".join(
            json.dumps({"candidate_id": f"CAND_{index:07d}"}) for index in range(1, 4)
        ),
        encoding="utf-8",
    )

    candidates = load_candidates(path, limit=2)

    assert len(candidates) == 2
    assert candidates[-1]["candidate_id"] == "CAND_0000002"


def test_unsupported_extension_raises_candidate_data_error(tmp_path):
    path = tmp_path / "candidates.txt"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(CandidateDataError):
        load_candidates(path)


def test_invalid_json_raises_candidate_data_error(tmp_path):
    path = tmp_path / "candidates.json"
    path.write_text("{not valid", encoding="utf-8")

    with pytest.raises(CandidateDataError):
        load_candidates(path)


def test_join_candidate_text_includes_title_skills_and_schema_fields():
    candidate = {
        "profile": {
            "headline": "Search ML engineer",
            "summary": "Works on recommender systems.",
            "current_title": "Senior Machine Learning Engineer",
            "current_company": "SearchWorks",
            "current_industry": "Internet",
            "location": "Bengaluru",
        },
        "career_history": [
            {
                "title": "Ranking Engineer",
                "company": "TalentGraph",
                "industry": "HR Tech",
                "description": "Built candidate recommendation pipelines.",
            }
        ],
        "skills": [{"name": "Learning to Rank"}, "Python"],
        "certifications": [{"name": "ML Specialization"}],
        "education": [{"degree": "M.Tech", "field_of_study": "Computer Science"}],
    }

    joined = join_candidate_text(candidate)

    assert "Senior Machine Learning Engineer" in joined
    assert "Learning to Rank" in joined
    assert "ML Specialization" in joined
    assert "Computer Science" in joined
