from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.ranking import RankedPreviewRow
from src.utils import sentence_join, shorten_list_text, unique_preserve_order


JD_CONNECTION_TERMS = (
    "ranking",
    "search",
    "retrieval",
    "recommendation",
    "embeddings",
    "vector",
    "evaluation",
    "production ML",
    "product engineering",
)

BANNED_REASONING_PHRASES = (
    "AI says",
    "LLM",
    "model thinks",
    "probably",
    "final_score_preview",
    "guardrail",
    "scorecard",
    "confirmed honeypot",
    "hidden ground truth",
)


@dataclass
class ReasoningInput:
    candidate_id: str
    preview_rank: int | None
    final_score_preview: float
    final_score_band: str
    title: str
    title_category: str
    years_of_experience: float | None
    location: str
    location_category: str
    static_fit_score: float
    redrob_availability_score: float
    behavior_band: str
    trap_severity_band: str
    applied_cap_codes: list[str]
    evidence_seeds: list[str]
    key_flags: dict[str, bool]
    debug_summary: str


@dataclass
class CandidateReasoning:
    candidate_id: str
    reasoning: str
    tone: str
    facts_used: list[str]
    concerns_used: list[str]
    jd_terms_used: list[str]
    quality_flags: dict[str, bool]


def clean_reason_text(text: object) -> str:
    cleaned = " ".join(str(text or "").replace("\n", " ").replace("\r", " ").split())
    return cleaned.strip("\"' ")


def trim_sentence(text: str, max_chars: int = 260) -> str:
    cleaned = clean_reason_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    clipped = cleaned[:max_chars].rstrip()
    punctuation_positions = [clipped.rfind(mark) for mark in (".", "!", "?")]
    punctuation = max(punctuation_positions)
    if punctuation >= max_chars * 0.60:
        return clipped[: punctuation + 1]
    space = clipped.rfind(" ")
    if space >= max_chars * 0.60:
        clipped = clipped[:space]
    return clipped.rstrip(" ,;:") + "."


def years_text(years: float | int | None) -> str:
    if not isinstance(years, (int, float)) or isinstance(years, bool):
        return "unknown experience"
    value = float(years)
    if value.is_integer():
        return f"{int(value)} years"
    return f"{value:.1f} years"


def split_applied_caps(applied_cap_codes: object) -> list[str]:
    if isinstance(applied_cap_codes, list):
        return unique_preserve_order([str(value) for value in applied_cap_codes])
    if isinstance(applied_cap_codes, str):
        return unique_preserve_order([part.strip() for part in applied_cap_codes.split(",")])
    return []


def reasoning_input_from_ranked_row(row: RankedPreviewRow) -> ReasoningInput:
    flat = row.flat_debug or {}
    key_flags = {
        key: bool(flat.get(key))
        for key in (
            "has_real_retrieval_or_ranking_evidence",
            "has_evaluation_evidence",
            "has_production_evidence",
            "wrong_role_title",
            "keyword_stuffing_shape",
            "consulting_only_career",
            "low_or_very_low_hireability",
            "high_or_extreme_trap_risk",
        )
    }
    return ReasoningInput(
        candidate_id=row.candidate_id,
        preview_rank=row.preview_rank,
        final_score_preview=row.final_score_preview,
        final_score_band=row.final_score_band,
        title=row.title,
        title_category=row.title_category,
        years_of_experience=row.years_of_experience,
        location=row.location,
        location_category=row.location_category,
        static_fit_score=row.static_fit_score,
        redrob_availability_score=row.redrob_availability_score,
        behavior_band=str(flat.get("behavior_band") or ""),
        trap_severity_band=str(flat.get("trap_severity_band") or ""),
        applied_cap_codes=split_applied_caps(row.applied_cap_codes or flat.get("applied_cap_codes")),
        evidence_seeds=[clean_reason_text(seed) for seed in row.evidence_seeds],
        key_flags=key_flags,
        debug_summary=clean_reason_text(row.debug_summary),
    )


def choose_reasoning_tone(input: ReasoningInput) -> str:
    high_trap = input.key_flags.get("high_or_extreme_trap_risk") or input.trap_severity_band in {
        "high_risk",
        "extreme_risk",
    }
    if input.final_score_band == "weak_fit" or high_trap:
        return "risky"
    if input.final_score_band == "elite_fit":
        return "elite"
    if input.final_score_band == "strong_fit" or (
        input.preview_rank is not None and input.preview_rank <= 10 and not high_trap
    ):
        return "strong"
    if input.final_score_band == "good_fit":
        return "good"
    return "borderline"


def select_positive_facts(input: ReasoningInput, max_facts: int = 3) -> list[str]:
    facts: list[str] = []
    seeds = input.evidence_seeds
    if input.key_flags.get("has_real_retrieval_or_ranking_evidence"):
        facts.append(_best_seed(seeds, ("ranking", "search", "retrieval", "recommendation", "faiss")) or "career evidence of ranking/search work")
    if input.key_flags.get("has_evaluation_evidence"):
        facts.append(_best_seed(seeds, ("ndcg", "mrr", "map", "a/b", "evaluation")) or "evaluation evidence for ranking quality")
    if input.key_flags.get("has_production_evidence"):
        facts.append(_best_seed(seeds, ("production", "shipped", "deployed", "owned")) or "production ML evidence")
    if input.years_of_experience is not None:
        facts.append(f"{years_text(input.years_of_experience)} of experience")
    if input.title:
        facts.append(f"{input.title} title")
    if input.location_category in {"preferred", "acceptable", "relocation_possible"} and input.location:
        facts.append(f"{input.location} location fit")
    if input.behavior_band in {"excellent_hireability", "good_hireability"}:
        facts.append(input.behavior_band.replace("_", " "))
    if input.key_flags.get("has_real_retrieval_or_ranking_evidence"):
        skill_seed = _best_seed(seeds, ("faiss", "pinecone", "bm25", "elasticsearch", "vector", "embeddings"))
        if skill_seed:
            facts.append(skill_seed)
    return [_fact_phrase(fact) for fact in unique_preserve_order(facts)[:max_facts]]


def select_concerns(input: ReasoningInput, max_concerns: int = 2) -> list[str]:
    concerns: list[str] = []
    caps = set(input.applied_cap_codes)
    if input.key_flags.get("high_or_extreme_trap_risk") or input.trap_severity_band in {"high_risk", "extreme_risk"}:
        concerns.append("profile has high trap-risk signals")
    if input.key_flags.get("wrong_role_title") or "wrong_role_keyword_stuffing" in caps:
        concerns.append("wrong-role keyword-stuffing risk")
    if "no_real_retrieval_or_ranking_evidence" in caps:
        concerns.append("limited real retrieval/ranking evidence")
    if "weak_ai_hype_without_production" in caps:
        concerns.append("weak AI-hype signals without enough production evidence")
    if "consulting_only_no_product" in caps:
        concerns.append("consulting-only profile without product retrieval evidence")
    if "non_target_ai_only" in caps:
        concerns.append("non-target AI focus for this retrieval-heavy JD")
    if input.key_flags.get("low_or_very_low_hireability") or input.behavior_band in {
        "low_hireability",
        "very_low_hireability",
    }:
        concerns.append("low Redrob hireability")
    if input.final_score_band == "weak_fit":
        concerns.append("overall JD fit is weaker than stronger preview matches")
    if any(term in input.debug_summary.lower() for term in ("notice", "low recruiter", "response")):
        concerns.append("availability or recruiter-response concern")
    if input.location_category in {"outside_india", "india_other"} and input.location:
        concerns.append(f"location logistics may be weaker from {input.location}")
    return unique_preserve_order(concerns)[:max_concerns]


def select_jd_terms(input: ReasoningInput, max_terms: int = 3) -> list[str]:
    text = " ".join(input.evidence_seeds).lower()
    terms: list[str] = []
    if input.key_flags.get("has_real_retrieval_or_ranking_evidence"):
        terms.append("ranking/search")
    if input.key_flags.get("has_real_retrieval_or_ranking_evidence") and "retrieval" in text:
        terms.append("retrieval")
    if input.key_flags.get("has_real_retrieval_or_ranking_evidence") and "recommendation" in text:
        terms.append("recommendation systems")
    if input.key_flags.get("has_real_retrieval_or_ranking_evidence") and any(
        term in text for term in ("embedding", "vector", "faiss", "pinecone")
    ):
        terms.append("embeddings/vector search")
    if input.key_flags.get("has_evaluation_evidence") or any(term in text for term in ("ndcg", "mrr", "map", "a/b", "evaluation")):
        terms.append("evaluation frameworks")
    if input.key_flags.get("has_production_evidence"):
        terms.append("production ML")
    return unique_preserve_order(terms)[:max_terms]


def build_positive_sentence(input: ReasoningInput, facts: list[str], jd_terms: list[str]) -> str:
    fact_text = shorten_list_text(facts, 3)
    jd_text = shorten_list_text(jd_terms, 3)
    tone = choose_reasoning_tone(input)
    if not fact_text:
        return "Included as a lower-confidence match because the available profile evidence is limited for the Senior AI Engineer JD."
    if tone in {"elite", "strong"}:
        prefix = "Strong fit"
    elif tone == "good":
        prefix = "Good fit"
    elif tone == "borderline":
        prefix = "Borderline fit"
    else:
        prefix = "Lower-confidence match"
    if jd_text:
        return f"{prefix}: {fact_text}, mapping to the JD's {jd_text} focus."
    return f"{prefix}: {fact_text}, but the link to the JD's retrieval/ranking focus is limited."


def build_concern_sentence(input: ReasoningInput, concerns: list[str]) -> str:
    if not concerns:
        return ""
    return f"Concern: {shorten_list_text(concerns, 2)}."


def generate_reasoning_from_input(input: ReasoningInput) -> CandidateReasoning:
    tone = choose_reasoning_tone(input)
    facts = select_positive_facts(input)
    concerns = select_concerns(input)
    if concerns:
        facts = _concern_mode_facts(input, facts)
    jd_terms = select_jd_terms(input)
    positive = build_positive_sentence(input, facts, jd_terms)
    concern = build_concern_sentence(input, concerns)
    positive = trim_sentence(positive, max_chars=360 if concern else 430)
    concern = trim_sentence(concern, max_chars=130)
    reasoning = trim_sentence(sentence_join([positive, concern], max_sentences=2), max_chars=450)
    if concern and "Concern:" not in reasoning:
        positive = trim_sentence(positive, max_chars=260)
        reasoning = trim_sentence(sentence_join([positive, concern], max_sentences=2), max_chars=450)
    reasoning = _remove_banned_phrases(reasoning)
    quality_flags = {
        "has_specific_fact": _has_specific_fact(reasoning),
        "has_jd_connection": any(term.lower() in reasoning.lower() for term in JD_CONNECTION_TERMS),
        "has_concern_if_needed": bool(concerns) == ("Concern:" in reasoning) or not concerns,
        "has_no_empty_reasoning": bool(reasoning),
        "likely_too_generic": _is_likely_generic(reasoning),
        "too_long": len(reasoning) > 500,
        "too_many_sentences": _count_sentences(reasoning) > 2,
    }
    return CandidateReasoning(
        candidate_id=input.candidate_id,
        reasoning=reasoning,
        tone=tone,
        facts_used=facts,
        concerns_used=concerns,
        jd_terms_used=jd_terms,
        quality_flags=quality_flags,
    )


def generate_reasoning_for_row(row: RankedPreviewRow) -> CandidateReasoning:
    return generate_reasoning_from_input(reasoning_input_from_ranked_row(row))


def _best_seed(seeds: list[str], terms: tuple[str, ...]) -> str:
    fallback = ""
    for seed in seeds:
        lower = seed.lower()
        if any(term in lower for term in terms):
            if lower.startswith("title:"):
                fallback = fallback or seed
                continue
            return seed
    return fallback


def _fact_phrase(value: str) -> str:
    cleaned = clean_reason_text(value).replace(".NET", "NET").rstrip(".!?;:")
    return _truncate_phrase(cleaned, 130, 90)


def _short_concern_fact(value: str) -> str:
    return _truncate_phrase(value, 105, 75)


def _concern_mode_facts(input: ReasoningInput, facts: list[str]) -> list[str]:
    selected: list[str] = []
    for fact in facts:
        lower = fact.lower()
        if " title" not in lower and " years" not in lower and "location fit" not in lower:
            selected.append(_short_concern_fact(fact))
            break
    if input.title:
        selected.append(f"{input.title} title")
    if input.location_category in {"preferred", "acceptable", "relocation_possible"} and input.location:
        selected.append(f"{input.location} location fit")
    if len(selected) < 3 and input.years_of_experience is not None:
        selected.append(f"{years_text(input.years_of_experience)} of experience")
    return unique_preserve_order(selected)[:3]


def _truncate_phrase(value: str, max_chars: int, min_space: int) -> str:
    cleaned = clean_reason_text(value).replace(".NET", "NET").rstrip(".!?;:")
    if len(cleaned) <= max_chars:
        return cleaned
    clipped = cleaned[:max_chars].rstrip()
    space = clipped.rfind(" ")
    if space >= min_space:
        clipped = clipped[:space]
    dangling_words = {
        "a",
        "an",
        "and",
        "or",
        "but",
        "than",
        "with",
        "using",
        "actually",
        "for",
        "the",
        "to",
        "that",
        "was",
        "were",
        "detect",
    }
    while clipped.split() and clipped.split()[-1].lower() in dangling_words:
        clipped = " ".join(clipped.split()[:-1])
    return clipped.rstrip(" ,;:—-")


def _remove_banned_phrases(text: str) -> str:
    cleaned = text
    for phrase in BANNED_REASONING_PHRASES:
        cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)
    return clean_reason_text(cleaned)


def _count_sentences(text: str) -> int:
    protected = re.sub(r"(?<=\d)\.(?=\d)", "<decimal>", text)
    protected = re.sub(r"\.NET", "NET", protected, flags=re.IGNORECASE)
    return len([part for part in re.split(r"[.!?]+", protected) if part.strip()])


def _has_specific_fact(text: str) -> bool:
    lower = text.lower()
    return bool(
        re.search(r"\b\d+(?:\.\d+)? years\b", lower)
        or any(term in lower for term in ("faiss", "pinecone", "ndcg", "mrr", "a/b", "bm25", "elasticsearch"))
        or any(term in lower for term in ("recommendation systems engineer", "production", "shipped", "deployed"))
        or any(city in lower for city in ("pune", "noida", "bengaluru", "bangalore", "hyderabad", "delhi"))
    )


def _is_likely_generic(text: str) -> bool:
    lower = text.lower().strip()
    generic_phrases = (
        "strong candidate with relevant skills",
        "good fit for the role",
        "has ai experience",
        "strong ai fit",
    )
    return any(phrase in lower for phrase in generic_phrases)
