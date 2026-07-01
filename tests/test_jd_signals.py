from __future__ import annotations

from src.jd_signals import (
    get_default_signal_map,
    match_terms,
    signal_map_to_markdown,
    summarize_signal_map,
)


def test_get_default_signal_map_returns_role_name():
    signal_map = get_default_signal_map()

    assert signal_map.role_name == "Senior AI Engineer"


def test_expected_signal_groups_exist():
    signal_map = get_default_signal_map()
    group_names = {group.name for group in signal_map.groups}

    assert {
        "target_titles",
        "adjacent_titles",
        "wrong_role_titles",
        "retrieval_ranking_core",
        "embedding_vector_search",
        "evaluation_frameworks",
        "production_evidence",
        "product_company_context",
        "service_company_context",
        "weak_ai_hype",
        "non_target_ai_specialties",
        "location_preferred",
        "location_acceptable",
        "education_relevance",
    } <= group_names


def test_match_terms_catches_faiss_under_embedding_vector_search():
    matches = match_terms("Built a production semantic search stack with FAISS.")

    assert "faiss" in matches["embedding_vector_search"]


def test_match_terms_catches_ndcg_under_evaluation_frameworks():
    matches = match_terms("Measured ranking quality with NDCG and recall@k.")

    assert "ndcg" in matches["evaluation_frameworks"]


def test_match_terms_catches_marketing_manager_under_wrong_role_titles():
    matches = match_terms("Marketing Manager with ChatGPT and prompt engineering projects.")

    assert "marketing manager" in matches["wrong_role_titles"]


def test_signal_map_to_markdown_contains_table():
    markdown = signal_map_to_markdown()

    assert "| Group | Strength | Applies To | Description | Example Terms |" in markdown


def test_summarize_signal_map_contains_role_name():
    summary = summarize_signal_map()

    assert "Senior AI Engineer" in summary
