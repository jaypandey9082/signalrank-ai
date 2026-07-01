from __future__ import annotations

import re
from functools import lru_cache
from typing import Any


def safe_lower(value: object) -> str:
    return normalize_whitespace(value).lower()


def normalize_whitespace(text: object) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_for_matching(text: object) -> str:
    normalized = normalize_whitespace(text).lower()
    if len(normalized) <= 160:
        return _normalize_for_matching_cached(normalized)
    return _normalize_for_matching_uncached(normalized)


@lru_cache(maxsize=8192)
def _normalize_for_matching_cached(normalized: str) -> str:
    return _normalize_for_matching_uncached(normalized)


def _normalize_for_matching_uncached(normalized: str) -> str:
    normalized = re.sub(r"[-_/|]", " ", normalized)
    normalized = re.sub(r"[^\w@+#\s]", " ", normalized)
    return normalize_whitespace(normalized)


def normalize_title(title: object) -> str:
    normalized = normalize_for_matching(title)
    seniority_words = {"senior", "lead", "principal", "staff", "jr", "junior"}
    words = [word for word in normalized.split() if word not in seniority_words]
    return normalize_whitespace(" ".join(words))


def normalize_location(location: object) -> str:
    normalized = normalize_for_matching(location)
    replacements = {
        "gurugram": "gurgaon",
        "bengaluru": "bangalore",
        "new delhi": "delhi",
    }
    return replacements.get(normalized, normalized)


def join_candidate_text(candidate: dict[str, Any]) -> str:
    """Join candidate text fields without assuming the full schema is present."""
    parts: list[str] = []

    profile = candidate.get("profile")
    if isinstance(profile, dict):
        _append_values(
            parts,
            profile,
            [
                "headline",
                "summary",
                "current_title",
                "current_company",
                "current_industry",
                "location",
            ],
        )

    career_history = candidate.get("career_history")
    if isinstance(career_history, list):
        for role in career_history:
            if isinstance(role, dict):
                _append_values(parts, role, ["title", "company", "industry", "description"])

    skills = candidate.get("skills")
    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict):
                _append_text(parts, skill.get("name"))
            else:
                _append_text(parts, skill)

    certifications = candidate.get("certifications")
    if isinstance(certifications, list):
        for certification in certifications:
            if isinstance(certification, dict):
                _append_text(parts, certification.get("name"))

    education = candidate.get("education")
    if isinstance(education, list):
        for item in education:
            if isinstance(item, dict):
                _append_values(parts, item, ["degree", "field_of_study"])

    return normalize_whitespace(" ".join(parts))


def _append_values(parts: list[str], source: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        _append_text(parts, source.get(key))


def _append_text(parts: list[str], value: object) -> None:
    normalized = normalize_whitespace(value)
    if normalized:
        parts.append(normalized)
