from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.features import (
    candidate_features_to_flat_dict,
    compact_feature_summary,
    extract_candidate_features,
)
from src.load_data import iter_candidates
from src.schema import validate_candidate
from src.utils import ensure_parent_dir


@dataclass
class FeatureInspectionReport:
    total_seen: int
    extracted_count: int
    extraction_error_count: int
    title_category_counts: dict[str, int]
    experience_band_counts: dict[str, int]
    location_category_counts: dict[str, int]
    candidates_with_real_retrieval_evidence: int
    candidates_with_evaluation_evidence: int
    candidates_with_production_evidence: int
    candidates_with_keyword_stuffing_shape: int
    candidates_with_wrong_role_title: int
    consulting_only_count: int
    top_current_titles: list[tuple[str, int]]
    top_skill_hits: list[tuple[str, int]]
    top_signal_groups: list[tuple[str, int]]
    sample_rows: list[dict[str, Any]]
    evidence_examples: list[dict[str, Any]]


def inspect_features(
    path: str | Path,
    limit: int | None = None,
    sample_size: int = 10,
) -> FeatureInspectionReport:
    total_seen = 0
    extracted_count = 0
    extraction_error_count = 0
    title_category_counts: Counter[str] = Counter()
    experience_band_counts: Counter[str] = Counter()
    location_category_counts: Counter[str] = Counter()
    current_titles: Counter[str] = Counter()
    skill_hits: Counter[str] = Counter()
    signal_groups: Counter[str] = Counter()
    sample_rows: list[dict[str, Any]] = []
    evidence_examples: list[dict[str, Any]] = []

    real_retrieval_count = 0
    evaluation_count = 0
    production_count = 0
    keyword_stuffing_count = 0
    wrong_role_count = 0
    consulting_only_count = 0

    for candidate in iter_candidates(path):
        if limit is not None and total_seen >= limit:
            break
        total_seen += 1

        validation = validate_candidate(candidate)
        if not validation.is_valid:
            extraction_error_count += 1
            continue

        try:
            features = extract_candidate_features(candidate)
        except (TypeError, ValueError, KeyError, AttributeError):
            extraction_error_count += 1
            continue

        extracted_count += 1
        title_category_counts[features.profile.title_category] += 1
        experience_band_counts[features.profile.experience_band] += 1
        location_category_counts[features.profile.location_category] += 1
        if features.profile.current_title:
            current_titles[features.profile.current_title] += 1

        for term in (
            features.skills.retrieval_ranking_skill_hits
            + features.skills.embedding_vector_skill_hits
            + features.skills.evaluation_skill_hits
            + features.skills.weak_ai_hype_skill_hits
            + features.skills.non_target_ai_skill_hits
        ):
            skill_hits[term] += 1

        for group_name, terms in features.matched_signal_terms.items():
            if terms:
                signal_groups[group_name] += 1

        flags = features.diagnostic_flags
        real_retrieval_count += int(flags.has_real_retrieval_or_ranking_evidence)
        evaluation_count += int(flags.has_evaluation_evidence)
        production_count += int(flags.has_production_evidence)
        keyword_stuffing_count += int(flags.has_keyword_stuffing_shape)
        wrong_role_count += int(flags.wrong_role_title)
        consulting_only_count += int(features.career.consulting_only_career)

        flat_row = candidate_features_to_flat_dict(features)
        if len(sample_rows) < sample_size:
            sample_rows.append(flat_row)

        if flags.has_real_retrieval_or_ranking_evidence and len(evidence_examples) < sample_size:
            evidence_examples.append(
                {
                    "candidate_id": features.candidate_id,
                    "summary": compact_feature_summary(features),
                    "snippets": features.career.career_evidence_snippets,
                }
            )

    return FeatureInspectionReport(
        total_seen=total_seen,
        extracted_count=extracted_count,
        extraction_error_count=extraction_error_count,
        title_category_counts=dict(title_category_counts),
        experience_band_counts=dict(experience_band_counts),
        location_category_counts=dict(location_category_counts),
        candidates_with_real_retrieval_evidence=real_retrieval_count,
        candidates_with_evaluation_evidence=evaluation_count,
        candidates_with_production_evidence=production_count,
        candidates_with_keyword_stuffing_shape=keyword_stuffing_count,
        candidates_with_wrong_role_title=wrong_role_count,
        consulting_only_count=consulting_only_count,
        top_current_titles=current_titles.most_common(10),
        top_skill_hits=skill_hits.most_common(15),
        top_signal_groups=signal_groups.most_common(15),
        sample_rows=sample_rows,
        evidence_examples=evidence_examples,
    )


def format_feature_console_report(report: FeatureInspectionReport) -> str:
    lines = [
        "SignalRank AI Feature Inspection",
        "================================",
        f"Total candidates seen: {report.total_seen}",
        f"Features extracted: {report.extracted_count}",
        f"Extraction errors or invalid records: {report.extraction_error_count}",
        "",
        "Title categories:",
        _format_dict(report.title_category_counts),
        "",
        "Experience bands:",
        _format_dict(report.experience_band_counts),
        "",
        "Location categories:",
        _format_dict(report.location_category_counts),
        "",
        "Diagnostic counts:",
        f"- real retrieval/ranking evidence: {report.candidates_with_real_retrieval_evidence}",
        f"- evaluation evidence: {report.candidates_with_evaluation_evidence}",
        f"- production evidence: {report.candidates_with_production_evidence}",
        f"- keyword-stuffing shape: {report.candidates_with_keyword_stuffing_shape}",
        f"- wrong-role title: {report.candidates_with_wrong_role_title}",
        f"- consulting-only career: {report.consulting_only_count}",
        "",
        "Top current titles:",
        _format_pairs(report.top_current_titles),
        "",
        "Top skill hits:",
        _format_pairs(report.top_skill_hits),
        "",
        "Top signal groups:",
        _format_pairs(report.top_signal_groups),
    ]

    if report.sample_rows:
        lines.extend(["", "Sample feature rows:"])
        for row in report.sample_rows:
            lines.append(
                "- "
                f"{row.get('candidate_id')} | {row.get('current_title')} | "
                f"{row.get('title_category')} | evidence: "
                f"{row.get('has_real_retrieval_or_ranking_evidence')}"
            )

    if report.evidence_examples:
        lines.extend(["", "Evidence examples:"])
        for example in report.evidence_examples:
            snippets = " / ".join(example.get("snippets", [])[:2])
            lines.append(f"- {example.get('candidate_id')}: {snippets}")

    return "\n".join(lines)


def format_feature_markdown_report(report: FeatureInspectionReport) -> str:
    lines = [
        "# Feature Inspection Report",
        "",
        "## Summary",
        "",
        f"- Total candidates seen: {report.total_seen}",
        f"- Features extracted: {report.extracted_count}",
        f"- Extraction errors or invalid records: {report.extraction_error_count}",
        "",
        "## Category Counts",
        "",
        "### Title Categories",
        _format_dict(report.title_category_counts),
        "",
        "### Experience Bands",
        _format_dict(report.experience_band_counts),
        "",
        "### Location Categories",
        _format_dict(report.location_category_counts),
        "",
        "## Diagnostic Counts",
        "",
        f"- Real retrieval/ranking evidence: {report.candidates_with_real_retrieval_evidence}",
        f"- Evaluation evidence: {report.candidates_with_evaluation_evidence}",
        f"- Production evidence: {report.candidates_with_production_evidence}",
        f"- Keyword-stuffing shape: {report.candidates_with_keyword_stuffing_shape}",
        f"- Wrong-role title: {report.candidates_with_wrong_role_title}",
        f"- Consulting-only career: {report.consulting_only_count}",
        "",
        "## Top Current Titles",
        _format_pairs(report.top_current_titles),
        "",
        "## Top Skill Hits",
        _format_pairs(report.top_skill_hits),
        "",
        "## Top Signal Groups",
        _format_pairs(report.top_signal_groups),
        "",
        "## Sample Rows",
    ]

    if report.sample_rows:
        for row in report.sample_rows:
            lines.append(
                "- "
                f"{row.get('candidate_id')}: {row.get('current_title')} "
                f"({row.get('title_category')})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Evidence Examples"])
    if report.evidence_examples:
        for example in report.evidence_examples:
            lines.append(f"- {example.get('candidate_id')}:")
            snippets = example.get("snippets", [])
            if snippets:
                lines.extend(f"  - {snippet}" for snippet in snippets)
            else:
                lines.append("  - No snippets captured")
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def feature_rows_to_csv(rows: list[dict[str, Any]], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["candidate_id"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_pairs(items: list[tuple[str, int]]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {name}: {count}" for name, count in items)


def _format_dict(values: dict[str, int]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {key}: {value}" for key, value in sorted(values.items()))
