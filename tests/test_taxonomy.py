from __future__ import annotations

from src import taxonomy


def test_all_terms_returns_set():
    terms = taxonomy.all_terms()

    assert isinstance(terms, set)


def test_all_terms_contains_important_terms():
    terms = taxonomy.all_terms()

    assert "faiss" in terms
    assert "ndcg" in terms
    assert "recommendation system" in terms
    assert "pune" in terms


def test_wrong_role_terms_include_marketing_manager():
    assert "marketing manager" in taxonomy.WRONG_ROLE_TITLES


def test_service_company_names_include_tcs():
    assert "tcs" in taxonomy.SERVICE_COMPANY_NAMES


def test_weak_ai_hype_terms_include_langchain():
    assert "langchain" in taxonomy.WEAK_AI_HYPE_TERMS
