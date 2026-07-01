from __future__ import annotations

from copy import deepcopy

from src.features import (
    CandidateFeatures,
    candidate_features_to_flat_dict,
    compact_feature_summary,
    extract_candidate_features,
)
from tests.test_schema import make_candidate


def test_extract_candidate_features_returns_dataclass():
    features = extract_candidate_features(make_candidate())

    assert isinstance(features, CandidateFeatures)
    assert features.candidate_id == "CAND_0000001"


def test_strong_ml_search_candidate_has_target_title_category():
    features = extract_candidate_features(make_candidate())

    assert features.profile.title_category == "target"


def test_marketing_manager_gets_wrong_role_title_category():
    candidate = make_candidate()
    candidate["profile"]["current_title"] = "Marketing Manager"

    features = extract_candidate_features(candidate)

    assert features.profile.title_category == "wrong_role"
    assert features.diagnostic_flags.wrong_role_title


def test_skill_hits_detect_vector_terms():
    candidate = make_candidate()
    candidate["skills"].append(
        {"name": "FAISS", "proficiency": "advanced", "endorsements": 4, "duration_months": 12}
    )
    candidate["skills"].append(
        {"name": "Pinecone", "proficiency": "advanced", "endorsements": 3, "duration_months": 8}
    )
    candidate["skills"].append(
        {"name": "Embeddings", "proficiency": "advanced", "endorsements": 5, "duration_months": 18}
    )

    features = extract_candidate_features(candidate)

    assert "faiss" in features.skills.embedding_vector_skill_hits
    assert "pinecone" in features.skills.embedding_vector_skill_hits
    assert "embeddings" in features.skills.embedding_vector_skill_hits


def test_career_hits_detect_ranking_retrieval_and_evaluation_terms():
    candidate = make_candidate()
    candidate["career_history"][0]["description"] = (
        "Shipped production ranking and retrieval pipelines with NDCG evaluation."
    )

    features = extract_candidate_features(candidate)

    assert "ranking" in features.career.retrieval_ranking_hits
    assert "retrieval" in features.career.retrieval_ranking_hits
    assert "ndcg" in features.career.evaluation_hits
    assert features.diagnostic_flags.has_real_retrieval_or_ranking_evidence


def test_salary_min_greater_than_max_sets_flag():
    candidate = make_candidate()
    candidate["redrob_signals"]["expected_salary_range_inr_lpa"] = {"min": 55, "max": 40}

    features = extract_candidate_features(candidate)

    assert features.diagnostic_flags.salary_range_invalid


def test_last_active_before_signup_sets_platform_dates_invalid():
    candidate = make_candidate()
    candidate["redrob_signals"]["signup_date"] = "2026-05-01"
    candidate["redrob_signals"]["last_active_date"] = "2026-04-01"

    features = extract_candidate_features(candidate)

    assert features.diagnostic_flags.platform_dates_invalid


def test_candidate_features_to_flat_dict_contains_expected_keys():
    features = extract_candidate_features(make_candidate())
    flat = candidate_features_to_flat_dict(features)

    assert "candidate_id" in flat
    assert "career_retrieval_ranking_hit_count" in flat
    assert "evidence_snippet_1" in flat


def test_compact_feature_summary_contains_candidate_id():
    features = extract_candidate_features(make_candidate())
    summary = compact_feature_summary(features)

    assert "CAND_0000001" in summary


def test_keyword_stuffing_shape_detects_skills_without_career_evidence():
    candidate = deepcopy(make_candidate())
    candidate["profile"]["current_title"] = "Marketing Manager"
    candidate["career_history"][0]["description"] = "Managed marketing campaigns and weekly content calendars."
    candidate["skills"] = [
        {"name": "FAISS", "proficiency": "advanced", "endorsements": 1, "duration_months": 2},
        {"name": "Pinecone", "proficiency": "advanced", "endorsements": 1, "duration_months": 2},
        {"name": "Embeddings", "proficiency": "advanced", "endorsements": 1, "duration_months": 2},
        {"name": "LangChain", "proficiency": "advanced", "endorsements": 1, "duration_months": 2},
    ]

    features = extract_candidate_features(candidate)

    assert features.diagnostic_flags.has_keyword_stuffing_shape
