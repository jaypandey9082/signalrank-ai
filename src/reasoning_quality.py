from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from src.reasoning import CandidateReasoning
from src.ranking import RankedPreviewRow


@dataclass
class ReasoningQualityIssue:
    candidate_id: str
    issue_code: str
    severity: str
    message: str


@dataclass
class ReasoningQualityReport:
    total_checked: int
    issue_count: int
    high_severity_count: int
    generic_count: int
    too_long_count: int
    empty_count: int
    missing_jd_connection_count: int
    missing_specific_fact_count: int
    rank_tone_mismatch_count: int
    repeated_reasoning_count: int
    issues: list[ReasoningQualityIssue]
    summary: str


def count_sentences(text: str) -> int:
    protected = re.sub(r"(?<=\d)\.(?=\d)", "<decimal>", str(text or ""))
    protected = re.sub(r"\.NET", "NET", protected, flags=re.IGNORECASE)
    return len([part for part in re.split(r"[.!?]+", protected) if part.strip()])


def is_too_generic(text: str) -> bool:
    lower = " ".join(str(text or "").lower().split())
    generic_phrases = (
        "strong candidate with relevant skills",
        "good fit for the role",
        "has ai experience",
        "strong ai fit",
        "relevant experience for the role",
    )
    return any(phrase in lower for phrase in generic_phrases)


def has_jd_connection(text: str) -> bool:
    lower = str(text or "").lower()
    return any(
        term in lower
        for term in (
            "ranking",
            "search",
            "retrieval",
            "recommendation",
            "embeddings",
            "vector",
            "evaluation",
            "production ml",
            "product engineering",
        )
    )


def has_specific_fact(text: str) -> bool:
    lower = str(text or "").lower()
    return bool(
        re.search(r"\b\d+(?:\.\d+)? years\b", lower)
        or any(term in lower for term in ("faiss", "pinecone", "ndcg", "mrr", "map", "a/b", "bm25", "elasticsearch"))
        or any(term in lower for term in ("production", "deployed", "shipped", "owned"))
        or any(city in lower for city in ("pune", "noida", "bengaluru", "bangalore", "hyderabad", "delhi"))
        or any(title in lower for title in ("engineer", "scientist", "analyst", "manager"))
    )


def check_rank_tone_mismatch(row: RankedPreviewRow, reasoning: CandidateReasoning) -> bool:
    text = reasoning.reasoning.lower()
    if row.final_score_preview < 0.42 and any(phrase in text for phrase in ("excellent", "elite", "top fit")):
        return True
    if row.preview_rank <= 10 and reasoning.tone == "risky" and "concern:" not in text:
        return True
    if row.final_score_band == "weak_fit" and reasoning.tone in {"elite", "strong"}:
        return True
    return False


def evaluate_reasoning_quality(
    rows: list[RankedPreviewRow],
    reasonings: list[CandidateReasoning],
) -> ReasoningQualityReport:
    by_id = {reasoning.candidate_id: reasoning for reasoning in reasonings}
    issues: list[ReasoningQualityIssue] = []
    text_counts = Counter(reasoning.reasoning for reasoning in reasonings if reasoning.reasoning)

    for row in rows:
        reasoning = by_id.get(row.candidate_id)
        if reasoning is None:
            issues.append(_issue(row.candidate_id, "missing_reasoning", "high", "No reasoning was generated."))
            continue
        text = reasoning.reasoning
        lower = text.lower()
        if not text.strip():
            issues.append(_issue(row.candidate_id, "empty_reasoning", "high", "Reasoning is empty."))
        if len(text) > 500:
            issues.append(_issue(row.candidate_id, "too_long", "medium", "Reasoning is longer than 500 characters."))
        if count_sentences(text) > 2:
            issues.append(_issue(row.candidate_id, "too_many_sentences", "medium", "Reasoning has more than 2 sentences."))
        if is_too_generic(text):
            issues.append(_issue(row.candidate_id, "too_generic", "medium", "Reasoning is too generic."))
        if not has_jd_connection(text):
            issues.append(_issue(row.candidate_id, "missing_jd_connection", "medium", "Reasoning lacks a JD connection."))
        if not has_specific_fact(text):
            issues.append(_issue(row.candidate_id, "missing_specific_fact", "medium", "Reasoning lacks a specific fact."))
        high_risk = row.flat_debug.get("high_or_extreme_trap_risk") or row.applied_cap_codes
        if high_risk and "concern:" not in lower:
            issues.append(_issue(row.candidate_id, "missing_concern", "medium", "Risky row does not acknowledge a concern."))
        if text and text_counts[text] > 1:
            issues.append(_issue(row.candidate_id, "repeated_reasoning", "low", "Reasoning is repeated across candidates."))
        if check_rank_tone_mismatch(row, reasoning):
            issues.append(_issue(row.candidate_id, "rank_tone_mismatch", "medium", "Reasoning tone does not match rank/score."))

    return _build_report(len(rows), issues)


def format_reasoning_quality_markdown(report: ReasoningQualityReport) -> str:
    lines = [
        "# Reasoning Quality Report",
        "",
        f"- Total checked: {report.total_checked}",
        f"- Issue count: {report.issue_count}",
        f"- High severity count: {report.high_severity_count}",
        f"- Generic count: {report.generic_count}",
        f"- Too long count: {report.too_long_count}",
        f"- Empty count: {report.empty_count}",
        f"- Missing JD connection count: {report.missing_jd_connection_count}",
        f"- Missing specific fact count: {report.missing_specific_fact_count}",
        f"- Rank tone mismatch count: {report.rank_tone_mismatch_count}",
        f"- Repeated reasoning count: {report.repeated_reasoning_count}",
        "",
        f"Summary: {report.summary}",
    ]
    if report.issues:
        lines.extend(["", "## Issues"])
        for issue in report.issues[:100]:
            lines.append(f"- {issue.candidate_id} | {issue.severity} | {issue.issue_code}: {issue.message}")
    return "\n".join(lines) + "\n"


def _issue(candidate_id: str, code: str, severity: str, message: str) -> ReasoningQualityIssue:
    return ReasoningQualityIssue(
        candidate_id=candidate_id,
        issue_code=code,
        severity=severity,
        message=message,
    )


def _build_report(total_checked: int, issues: list[ReasoningQualityIssue]) -> ReasoningQualityReport:
    counts = Counter(issue.issue_code for issue in issues)
    high = sum(1 for issue in issues if issue.severity == "high")
    summary = "Reasoning quality checks passed." if not issues else "Reasoning quality issues need review."
    return ReasoningQualityReport(
        total_checked=total_checked,
        issue_count=len(issues),
        high_severity_count=high,
        generic_count=counts["too_generic"],
        too_long_count=counts["too_long"],
        empty_count=counts["empty_reasoning"] + counts["missing_reasoning"],
        missing_jd_connection_count=counts["missing_jd_connection"],
        missing_specific_fact_count=counts["missing_specific_fact"],
        rank_tone_mismatch_count=counts["rank_tone_mismatch"],
        repeated_reasoning_count=counts["repeated_reasoning"],
        issues=issues,
        summary=summary,
    )
