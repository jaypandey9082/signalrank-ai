from __future__ import annotations

from src.evidence import count_matches, find_evidence_snippets, find_term_matches, split_sentences


def test_split_sentences_returns_fragments():
    sentences = split_sentences("Built ranking. Shipped search! Measured NDCG?\nOwned rollout.")

    assert sentences == ["Built ranking", "Shipped search", "Measured NDCG", "Owned rollout"]


def test_find_term_matches_is_case_insensitive():
    matches = find_term_matches("Built FAISS retrieval", ["faiss", "ndcg"])

    assert matches == ["faiss"]


def test_find_evidence_snippets_returns_source_text_only():
    text = "Owned ranking pipelines. Unrelated sentence."
    snippets = find_evidence_snippets(text, ["ranking"])

    assert snippets == ["Owned ranking pipelines"]
    assert snippets[0] in text


def test_count_matches_deduplicates_repeated_terms():
    count = count_matches("ranking ranking ranking with FAISS", ["ranking", "faiss"])

    assert count == 2
