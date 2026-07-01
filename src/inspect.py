from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

from src.load_data import iter_candidates
from src.schema import candidate_brief, validate_candidate


@dataclass
class DatasetInspection:
    total_seen: int
    valid_count: int
    invalid_count: int
    warning_count: int
    duplicate_candidate_ids: int
    top_titles: list[tuple[str, int]]
    top_locations: list[tuple[str, int]]
    top_countries: list[tuple[str, int]]
    top_industries: list[tuple[str, int]]
    top_skills: list[tuple[str, int]]
    experience_summary: dict[str, Any]
    redrob_summary: dict[str, Any]
    common_errors: list[tuple[str, int]]
    common_warnings: list[tuple[str, int]]
    sample_briefs: list[dict[str, Any]]


def inspect_candidates(
    path: str | Path,
    limit: int | None = None,
    sample_size: int = 5,
    strict: bool = False,
) -> DatasetInspection:
    total_seen = 0
    valid_count = 0
    invalid_count = 0
    warning_count = 0
    duplicate_candidate_ids = 0

    seen_ids: set[str] = set()
    titles: Counter[str] = Counter()
    locations: Counter[str] = Counter()
    countries: Counter[str] = Counter()
    industries: Counter[str] = Counter()
    skills: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    warnings: Counter[str] = Counter()

    experience_values: list[float] = []
    response_rates: list[float] = []
    notice_periods: list[float] = []
    open_to_work_true_count = 0
    willing_to_relocate_true_count = 0
    verified_email_true_count = 0
    verified_phone_true_count = 0
    linkedin_connected_true_count = 0
    redrob_seen_count = 0
    sample_briefs: list[dict[str, Any]] = []

    for candidate in iter_candidates(path):
        if limit is not None and total_seen >= limit:
            break

        total_seen += 1
        result = validate_candidate(candidate, strict=strict)
        if result.is_valid:
            valid_count += 1
        else:
            invalid_count += 1

        warning_count += len(result.warnings)
        for issue in result.errors:
            errors[_format_issue(issue.path, issue.message)] += 1
        for issue in result.warnings:
            warnings[_format_issue(issue.path, issue.message)] += 1

        candidate_id = candidate.get("candidate_id")
        if isinstance(candidate_id, str):
            if candidate_id in seen_ids:
                duplicate_candidate_ids += 1
            else:
                seen_ids.add(candidate_id)

        profile = candidate.get("profile")
        if isinstance(profile, dict):
            _count_text(titles, profile.get("current_title"))
            _count_text(locations, profile.get("location"))
            _count_text(countries, profile.get("country"))
            _count_text(industries, profile.get("current_industry"))
            _append_number(experience_values, profile.get("years_of_experience"))

        _count_skill_names(skills, candidate.get("skills"))
        redrob_seen_count += _collect_redrob_values(
            candidate.get("redrob_signals"),
            response_rates,
            notice_periods,
        )

        redrob = candidate.get("redrob_signals")
        if isinstance(redrob, dict):
            open_to_work_true_count += int(redrob.get("open_to_work_flag") is True)
            willing_to_relocate_true_count += int(redrob.get("willing_to_relocate") is True)
            verified_email_true_count += int(redrob.get("verified_email") is True)
            verified_phone_true_count += int(redrob.get("verified_phone") is True)
            linkedin_connected_true_count += int(redrob.get("linkedin_connected") is True)

        if len(sample_briefs) < sample_size:
            sample_briefs.append(candidate_brief(candidate))

    return DatasetInspection(
        total_seen=total_seen,
        valid_count=valid_count,
        invalid_count=invalid_count,
        warning_count=warning_count,
        duplicate_candidate_ids=duplicate_candidate_ids,
        top_titles=titles.most_common(10),
        top_locations=locations.most_common(10),
        top_countries=countries.most_common(10),
        top_industries=industries.most_common(10),
        top_skills=skills.most_common(15),
        experience_summary=_experience_summary(experience_values),
        redrob_summary={
            "open_to_work_true_count": open_to_work_true_count,
            "open_to_work_rate": _rate(open_to_work_true_count, redrob_seen_count),
            "avg_recruiter_response_rate": _average(response_rates),
            "avg_notice_period_days": _average(notice_periods),
            "willing_to_relocate_rate": _rate(willing_to_relocate_true_count, redrob_seen_count),
            "verified_email_rate": _rate(verified_email_true_count, redrob_seen_count),
            "verified_phone_rate": _rate(verified_phone_true_count, redrob_seen_count),
            "linkedin_connected_rate": _rate(linkedin_connected_true_count, redrob_seen_count),
        },
        common_errors=errors.most_common(10),
        common_warnings=warnings.most_common(10),
        sample_briefs=sample_briefs,
    )


def format_console_report(report: DatasetInspection) -> str:
    lines = [
        "SignalRank AI Data Inspection",
        "=" * 29,
        f"Total candidates seen: {report.total_seen}",
        f"Valid candidates: {report.valid_count}",
        f"Invalid candidates: {report.invalid_count}",
        f"Warnings: {report.warning_count}",
        f"Duplicate candidate IDs: {report.duplicate_candidate_ids}",
        "",
        "Top titles:",
        _format_pairs(report.top_titles),
        "",
        "Top skills:",
        _format_pairs(report.top_skills),
        "",
        "Experience:",
        _format_dict(report.experience_summary),
        "",
        "Redrob signals:",
        _format_dict(report.redrob_summary),
        "",
        "Common errors:",
        _format_pairs(report.common_errors),
        "",
        "Common warnings:",
        _format_pairs(report.common_warnings),
    ]

    if report.sample_briefs:
        lines.extend(["", "Sample briefs:"])
        for brief in report.sample_briefs:
            lines.append(
                "- "
                f"{brief.get('candidate_id')}: {brief.get('current_title')} at "
                f"{brief.get('current_company')} ({brief.get('validation_status')})"
            )

    return "\n".join(lines)


def format_markdown_report(report: DatasetInspection) -> str:
    lines = [
        "# Dataset Inspection Report",
        "",
        "## Summary",
        "",
        f"- Total candidates seen: {report.total_seen}",
        f"- Valid candidates: {report.valid_count}",
        f"- Invalid candidates: {report.invalid_count}",
        f"- Warnings: {report.warning_count}",
        f"- Duplicate candidate IDs: {report.duplicate_candidate_ids}",
        "",
        "## Top Fields",
        "",
        "### Titles",
        _format_markdown_pairs(report.top_titles),
        "",
        "### Locations",
        _format_markdown_pairs(report.top_locations),
        "",
        "### Countries",
        _format_markdown_pairs(report.top_countries),
        "",
        "### Industries",
        _format_markdown_pairs(report.top_industries),
        "",
        "### Skills",
        _format_markdown_pairs(report.top_skills),
        "",
        "## Experience Summary",
        _format_markdown_dict(report.experience_summary),
        "",
        "## Redrob Summary",
        _format_markdown_dict(report.redrob_summary),
        "",
        "## Common Errors",
        _format_markdown_pairs(report.common_errors),
        "",
        "## Common Warnings",
        _format_markdown_pairs(report.common_warnings),
        "",
        "## Sample Briefs",
    ]

    if not report.sample_briefs:
        lines.append("- None")
    else:
        for brief in report.sample_briefs:
            lines.append(
                "- "
                f"{brief.get('candidate_id')}: {brief.get('current_title')} at "
                f"{brief.get('current_company')} - {brief.get('validation_status')}"
            )

    return "\n".join(lines) + "\n"


def _collect_redrob_values(
    redrob: Any,
    response_rates: list[float],
    notice_periods: list[float],
) -> int:
    if not isinstance(redrob, dict):
        return 0
    _append_number(response_rates, redrob.get("recruiter_response_rate"))
    _append_number(notice_periods, redrob.get("notice_period_days"))
    return 1


def _experience_summary(values: list[float]) -> dict[str, Any]:
    bands = {"0-3": 0, "3-5": 0, "5-9": 0, "9-12": 0, "12+": 0}
    for value in values:
        if value < 3:
            bands["0-3"] += 1
        elif value < 5:
            bands["3-5"] += 1
        elif value < 9:
            bands["5-9"] += 1
        elif value < 12:
            bands["9-12"] += 1
        else:
            bands["12+"] += 1

    if not values:
        return {"min": None, "max": None, "average": None, "median": None, "count": 0, "bands": bands}

    return {
        "min": min(values),
        "max": max(values),
        "average": round(mean(values), 2),
        "median": median(values),
        "count": len(values),
        "bands": bands,
    }


def _append_number(values: list[float], value: Any) -> None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        values.append(float(value))


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(mean(values), 3)


def _rate(true_count: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(true_count / total, 3)


def _count_text(counter: Counter[str], value: Any) -> None:
    if isinstance(value, str) and value.strip():
        counter[value.strip()] += 1


def _count_skill_names(counter: Counter[str], skills: Any) -> None:
    if not isinstance(skills, list):
        return
    for skill in skills:
        if isinstance(skill, dict):
            _count_text(counter, skill.get("name"))
        elif isinstance(skill, str):
            _count_text(counter, skill)


def _format_issue(path: str, message: str) -> str:
    return f"{path}: {message}"


def _format_pairs(items: list[tuple[str, int]]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {name}: {count}" for name, count in items)


def _format_markdown_pairs(items: list[tuple[str, int]]) -> str:
    return _format_pairs(items)


def _format_dict(values: dict[str, Any]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {key}: {value}" for key, value in values.items())


def _format_markdown_dict(values: dict[str, Any]) -> str:
    return _format_dict(values)
