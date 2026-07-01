from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from src.normalize import normalize_for_matching
from src import taxonomy


@dataclass(frozen=True)
class SignalGroup:
    name: str
    description: str
    terms: tuple[str, ...]
    strength: str
    applies_to: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class JobSignalMap:
    role_name: str
    summary: str
    groups: tuple[SignalGroup, ...]


def get_default_signal_map() -> JobSignalMap:
    return JobSignalMap(
        role_name="Senior AI Engineer",
        summary=(
            "Founding-team AI engineering role focused on production ranking, "
            "retrieval, recommendation, embeddings, evaluation, and shipping."
        ),
        groups=(
            SignalGroup(
                "target_titles",
                "Titles that directly match senior AI/search/recommendation engineering work.",
                taxonomy.STRONG_TARGET_TITLES,
                "strong",
                ("profile.current_title", "career_history.title"),
            ),
            SignalGroup(
                "adjacent_titles",
                "Engineering titles that can be relevant when backed by ML/search evidence.",
                taxonomy.ADJACENT_ENGINEERING_TITLES,
                "weak",
                ("profile.current_title", "career_history.title"),
            ),
            SignalGroup(
                "wrong_role_titles",
                "Non-target roles that should not rank high from AI keywords alone.",
                taxonomy.WRONG_ROLE_TITLES,
                "negative",
                ("profile.current_title", "career_history.title"),
            ),
            SignalGroup(
                "retrieval_ranking_core",
                "Direct evidence of ranking, search, retrieval, recommendation, or matching systems.",
                taxonomy.CORE_RETRIEVAL_RANKING_TERMS,
                "strong",
                ("profile.summary", "career_history.description", "skills.name"),
            ),
            SignalGroup(
                "embedding_vector_search",
                "Evidence of embeddings, vector search, ANN indexes, or hybrid retrieval systems.",
                taxonomy.EMBEDDING_VECTOR_TERMS,
                "strong",
                ("profile.summary", "career_history.description", "skills.name"),
            ),
            SignalGroup(
                "evaluation_frameworks",
                "Ranking and retrieval evaluation signals such as NDCG, MRR, relevance labels, or A/B tests.",
                taxonomy.EVALUATION_TERMS,
                "strong",
                ("profile.summary", "career_history.description", "skills.name"),
            ),
            SignalGroup(
                "production_evidence",
                "Signs that work was shipped, owned, measured, and maintained for real users.",
                taxonomy.PRODUCTION_EVIDENCE_TERMS,
                "strong",
                ("profile.summary", "career_history.description", "redrob_signals"),
            ),
            SignalGroup(
                "product_company_context",
                "Industries and company contexts where product search/recommendation work is likely.",
                taxonomy.PRODUCT_COMPANY_INDUSTRIES,
                "medium",
                ("profile.current_industry", "career_history.industry"),
            ),
            SignalGroup(
                "service_company_context",
                "Service-company context that may need product evidence before ranking highly.",
                taxonomy.SERVICE_COMPANY_NAMES,
                "negative",
                ("profile.current_company", "career_history.company"),
                "Not a rejection signal by itself; later scoring should check for product evidence.",
            ),
            SignalGroup(
                "weak_ai_hype",
                "AI buzzwords or side-project signals that are weak without production ML evidence.",
                taxonomy.WEAK_AI_HYPE_TERMS,
                "weak",
                ("profile.summary", "career_history.description", "skills.name"),
            ),
            SignalGroup(
                "non_target_ai_specialties",
                "AI specialties that are useful but less central than NLP/IR/retrieval for this JD.",
                taxonomy.NON_TARGET_AI_SPECIALTIES,
                "weak",
                ("profile.summary", "career_history.description", "skills.name"),
            ),
            SignalGroup(
                "location_preferred",
                "Preferred locations for the role.",
                taxonomy.PREFERRED_LOCATIONS,
                "medium",
                ("profile.location",),
            ),
            SignalGroup(
                "location_acceptable",
                "Other acceptable India locations for logistics.",
                taxonomy.ACCEPTABLE_LOCATIONS,
                "medium",
                ("profile.location",),
            ),
            SignalGroup(
                "education_relevance",
                "Education fields that support AI/ML/data engineering readiness.",
                taxonomy.EDUCATION_SIGNAL_FIELDS,
                "medium",
                ("education.degree", "education.field_of_study"),
            ),
        ),
    )


def flatten_signal_terms(signal_map: JobSignalMap | None = None) -> dict[str, list[str]]:
    active_map = signal_map or get_default_signal_map()
    return {group.name: list(group.terms) for group in active_map.groups}


def match_terms(text: str, signal_map: JobSignalMap | None = None) -> dict[str, list[str]]:
    active_map = signal_map or get_default_signal_map()
    normalized_text = f" {normalize_for_matching(text)} "
    matches: dict[str, list[str]] = {}

    for group in active_map.groups:
        group_matches: list[str] = []
        for term, normalized_term in _normalized_terms(group.terms):
            if normalized_term and f" {normalized_term} " in normalized_text:
                group_matches.append(term)
        if group_matches:
            matches[group.name] = group_matches

    return matches


def summarize_signal_map(signal_map: JobSignalMap | None = None) -> str:
    active_map = signal_map or get_default_signal_map()
    lines = [
        f"{active_map.role_name} Signal Map",
        "=" * (len(active_map.role_name) + 11),
        active_map.summary,
        "",
    ]
    for group in active_map.groups:
        examples = ", ".join(group.terms[:5])
        lines.append(f"- {group.name} ({group.strength}): {group.description}")
        lines.append(f"  Applies to: {', '.join(group.applies_to)}")
        lines.append(f"  Example terms: {examples}")
        if group.notes:
            lines.append(f"  Notes: {group.notes}")
    return "\n".join(lines)


def signal_map_to_markdown(signal_map: JobSignalMap | None = None) -> str:
    active_map = signal_map or get_default_signal_map()
    lines = [
        f"# {active_map.role_name} Signal Map",
        "",
        active_map.summary,
        "",
        "| Group | Strength | Applies To | Description | Example Terms |",
        "| --- | --- | --- | --- | --- |",
    ]
    for group in active_map.groups:
        lines.append(
            "| "
            f"{group.name} | "
            f"{group.strength} | "
            f"{', '.join(group.applies_to)} | "
            f"{group.description} | "
            f"{', '.join(group.terms[:6])} |"
        )
    return "\n".join(lines) + "\n"


@lru_cache(maxsize=128)
def _normalized_terms(terms: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((term, normalize_for_matching(term)) for term in terms)
