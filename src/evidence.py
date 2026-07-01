from __future__ import annotations

import re
from functools import lru_cache

from src.normalize import normalize_for_matching, normalize_whitespace


def split_sentences(text: object) -> list[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []
    return [
        normalize_whitespace(fragment)
        for fragment in re.split(r"[.!?\n]+", normalized)
        if normalize_whitespace(fragment)
    ]


def find_term_matches(text: object, terms: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    normalized_text = f" {normalize_for_matching(text)} "
    matches: list[str] = []
    seen: set[str] = set()

    for term, normalized_term in _normalized_terms(tuple(terms)):
        if not normalized_term or normalized_term in seen:
            continue
        if f" {normalized_term} " in normalized_text:
            matches.append(term)
            seen.add(normalized_term)

    return matches


def find_evidence_snippets(
    text: object,
    terms: list[str] | tuple[str, ...] | set[str],
    max_snippets: int = 3,
    max_chars: int = 220,
) -> list[str]:
    snippets: list[str] = []
    seen: set[str] = set()

    for sentence in split_sentences(text):
        if not find_term_matches(sentence, terms):
            continue
        snippet = _trim_snippet(sentence, max_chars)
        key = normalize_for_matching(snippet)
        if key and key not in seen:
            snippets.append(snippet)
            seen.add(key)
        if len(snippets) >= max_snippets:
            break

    return snippets


def count_matches(text: object, terms: list[str] | tuple[str, ...] | set[str]) -> int:
    return len(find_term_matches(text, terms))


def _trim_snippet(sentence: str, max_chars: int) -> str:
    if len(sentence) <= max_chars:
        return sentence
    trimmed = sentence[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{trimmed}..." if trimmed else sentence[:max_chars]


@lru_cache(maxsize=128)
def _normalized_terms(terms: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((term, normalize_for_matching(term)) for term in terms)
