from __future__ import annotations

from copy import deepcopy

from src.features import extract_candidate_features
from src.scoring import (
    clamp01,
    compute_static_scorecard,
    score_career_evidence,
    score_candidate,
    score_evaluation_experience,
    score_experience_fit,
    scorecard_to_flat_dict,
)
from src.scoring_config import validate_static_fit_weights
from tests.test_schema import make_candidate


def make_strong_candidate() -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = "CAND_0000101"
    candidate["profile"]["current_title"] = "Recommendation Systems Engineer"
    candidate["profile"]["years_of_experience"] = 6.5
    candidate["profile"]["current_industry"] = "Food Delivery"
    candidate["profile"]["location"] = "Pune"
    candidate["career_history"][0]["industry"] = "Food Delivery"
    candidate["career_history"][0]["title"] = "Recommendation Systems Engineer"
    candidate["career_history"][0]["description"] = (
        "Shipped production ranking model for search relevance using FAISS retrieval. "
        "Measured NDCG, MRR, and A/B test results for real users."
    )
    candidate["skills"] = [
        {"name": "Recommendation Systems", "proficiency": "expert", "endorsements": 30, "duration_months": 60},
        {"name": "FAISS", "proficiency": "advanced", "endorsements": 12, "duration_months": 30},
        {"name": "NDCG", "proficiency": "advanced", "endorsements": 8, "duration_months": 24},
    ]
    return candidate


def make_keyword_stuffer() -> dict:
    candidate = make_candidate()
    candidate["candidate_id"] = "CAND_0000102"
    candidate["profile"]["current_title"] = "Marketing Manager"
    candidate["profile"]["summary"] = "AI tools enthusiast with ChatGPT experiments."
    candidate["career_history"][0]["title"] = "Marketing Manager"
    candidate["career_history"][0]["industry"] = "Marketing"
    candidate["career_history"][0]["description"] = (
        "Managed content calendars, campaign analytics, and SEO workflows for brand marketing."
    )
    candidate["skills"] = [
        {"name": "LangChain", "proficiency": "expert", "endorsements": 5, "duration_months": 4},
        {"name": "Pinecone", "proficiency": "expert", "endorsements": 4, "duration_months": 3},
        {"name": "Prompt Engineering", "proficiency": "expert", "endorsements": 7, "duration_months": 5},
        {"name": "Embeddings", "proficiency": "expert", "endorsements": 4, "duration_months": 3},
    ]
    return candidate


def test_clamp01_handles_edges():
    assert clamp01(-1) == 0.0
    assert clamp01(1.5) == 1.0
    assert clamp01(None) == 0.0


def test_validate_static_fit_weights_returns_true():
    assert validate_static_fit_weights()


def test_score_experience_fit_gives_ideal_band_high_score():
    candidate = make_candidate()
    candidate["profile"]["years_of_experience"] = 6.5
    component = score_experience_fit(extract_candidate_features(candidate))

    assert component.raw_score == 1.0


def test_target_title_gets_higher_career_support_than_wrong_role_title():
    target = extract_candidate_features(make_strong_candidate())
    wrong = extract_candidate_features(make_keyword_stuffer())

    assert score_career_evidence(target).raw_score > score_career_evidence(wrong).raw_score


def test_strong_candidate_scores_higher_than_keyword_stuffer():
    strong = score_candidate(make_strong_candidate())
    weak = score_candidate(make_keyword_stuffer())

    assert strong.static_fit_score > weak.static_fit_score


def test_skills_only_ai_candidate_is_capped():
    scorecard = score_candidate(make_keyword_stuffer())

    assert scorecard.static_fit_score < 0.65


def test_career_ranking_and_production_gets_high_career_score():
    features = extract_candidate_features(make_strong_candidate())
    component = score_career_evidence(features)

    assert component.raw_score >= 0.70


def test_evaluation_terms_get_nonzero_evaluation_score():
    features = extract_candidate_features(make_strong_candidate())
    component = score_evaluation_experience(features)

    assert component.raw_score > 0


def test_compute_static_scorecard_returns_score_between_zero_and_one():
    features = extract_candidate_features(make_candidate())
    scorecard = compute_static_scorecard(features)

    assert 0 <= scorecard.static_fit_score <= 1


def test_scorecard_to_flat_dict_includes_component_columns():
    scorecard = score_candidate(make_strong_candidate())
    flat = scorecard_to_flat_dict(scorecard)

    assert "static_fit_score" in flat
    assert "career_evidence_raw" in flat
    assert "career_evidence_weighted" in flat


def test_wrong_role_with_copied_skills_stays_below_strong_candidate():
    weak = make_keyword_stuffer()
    strong = make_strong_candidate()
    weak["skills"] = deepcopy(strong["skills"])

    assert score_candidate(strong).static_fit_score > score_candidate(weak).static_fit_score
