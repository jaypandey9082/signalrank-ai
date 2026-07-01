from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any


REQUIRED_TOP_LEVEL_FIELDS = [
    "candidate_id",
    "profile",
    "career_history",
    "education",
    "skills",
    "redrob_signals",
]

REQUIRED_PROFILE_FIELDS = [
    "anonymized_name",
    "headline",
    "summary",
    "location",
    "country",
    "years_of_experience",
    "current_title",
    "current_company",
    "current_company_size",
    "current_industry",
]

REQUIRED_CAREER_FIELDS = [
    "company",
    "title",
    "start_date",
    "end_date",
    "duration_months",
    "is_current",
    "industry",
    "company_size",
    "description",
]

REQUIRED_SKILL_FIELDS = [
    "name",
    "proficiency",
    "endorsements",
]

REQUIRED_REDROB_FIELDS = [
    "profile_completeness_score",
    "signup_date",
    "last_active_date",
    "open_to_work_flag",
    "profile_views_received_30d",
    "applications_submitted_30d",
    "recruiter_response_rate",
    "avg_response_time_hours",
    "skill_assessment_scores",
    "connection_count",
    "endorsements_received",
    "notice_period_days",
    "expected_salary_range_inr_lpa",
    "preferred_work_mode",
    "willing_to_relocate",
    "github_activity_score",
    "search_appearance_30d",
    "saved_by_recruiters_30d",
    "interview_completion_rate",
    "offer_acceptance_rate",
    "verified_email",
    "verified_phone",
    "linkedin_connected",
]

VALID_SKILL_PROFICIENCIES = {"beginner", "intermediate", "advanced", "expert"}
_CANDIDATE_ID_RE = re.compile(r"^CAND_[0-9]{7}$")


@dataclass
class ValidationIssue:
    path: str
    message: str
    severity: str


@dataclass
class ValidationResult:
    candidate_id: str | None
    is_valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]


def is_valid_candidate_id(candidate_id: object) -> bool:
    return isinstance(candidate_id, str) and bool(_CANDIDATE_ID_RE.fullmatch(candidate_id))


def validate_candidate(candidate: dict[str, Any], strict: bool = False) -> ValidationResult:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if not isinstance(candidate, dict):
        errors.append(_issue("$", "candidate must be a JSON object", "error"))
        return ValidationResult(None, False, errors, warnings)

    candidate_id = candidate.get("candidate_id")
    if not is_valid_candidate_id(candidate_id):
        errors.append(
            _issue(
                "candidate_id",
                "candidate_id must match CAND_ followed by 7 digits",
                "error",
            )
        )

    _check_required(candidate, REQUIRED_TOP_LEVEL_FIELDS, "", errors)

    profile = candidate.get("profile")
    if not isinstance(profile, dict):
        errors.append(_issue("profile", "profile must be an object", "error"))
        profile = {}
    else:
        _check_required(profile, REQUIRED_PROFILE_FIELDS, "profile", errors)
        _check_number_range(
            profile.get("years_of_experience"),
            "profile.years_of_experience",
            0,
            50,
            errors if strict else warnings,
            "error" if strict else "warning",
        )

    career_history = candidate.get("career_history")
    if not isinstance(career_history, list):
        errors.append(_issue("career_history", "career_history must be a list", "error"))
        career_history = []
    elif not career_history:
        errors.append(_issue("career_history", "career_history must contain at least one role", "error"))
    else:
        _validate_career_history(career_history, errors, warnings, strict)

    skills = candidate.get("skills")
    if not isinstance(skills, list):
        errors.append(_issue("skills", "skills must be a list", "error"))
        skills = []
    else:
        _validate_skills(skills, errors, warnings, strict)

    education = candidate.get("education")
    if not isinstance(education, list):
        errors.append(_issue("education", "education must be a list", "error"))

    redrob = candidate.get("redrob_signals")
    if not isinstance(redrob, dict):
        errors.append(_issue("redrob_signals", "redrob_signals must be an object", "error"))
        redrob = {}
    else:
        _check_required(redrob, REQUIRED_REDROB_FIELDS, "redrob_signals", errors)
        _validate_redrob_signals(redrob, errors, warnings, strict)

    return ValidationResult(
        candidate_id=candidate_id if isinstance(candidate_id, str) else None,
        is_valid=not errors,
        errors=errors,
        warnings=warnings,
    )


def candidate_brief(candidate: dict[str, Any]) -> dict[str, Any]:
    profile = candidate.get("profile") if isinstance(candidate, dict) else {}
    if not isinstance(profile, dict):
        profile = {}
    redrob = candidate.get("redrob_signals") if isinstance(candidate, dict) else {}
    if not isinstance(redrob, dict):
        redrob = {}
    skills = candidate.get("skills") if isinstance(candidate, dict) else []
    if not isinstance(skills, list):
        skills = []
    career_history = candidate.get("career_history") if isinstance(candidate, dict) else []
    if not isinstance(career_history, list):
        career_history = []

    result = validate_candidate(candidate if isinstance(candidate, dict) else {})
    return {
        "candidate_id": candidate.get("candidate_id") if isinstance(candidate, dict) else None,
        "current_title": profile.get("current_title"),
        "current_company": profile.get("current_company"),
        "location": profile.get("location"),
        "country": profile.get("country"),
        "years_of_experience": profile.get("years_of_experience"),
        "skill_count": len(skills),
        "career_roles": len(career_history),
        "top_skills": _skill_names(skills)[:5],
        "open_to_work": redrob.get("open_to_work_flag"),
        "last_active_date": redrob.get("last_active_date"),
        "recruiter_response_rate": redrob.get("recruiter_response_rate"),
        "notice_period_days": redrob.get("notice_period_days"),
        "validation_status": "valid" if result.is_valid else "invalid",
    }


def _validate_career_history(
    career_history: list[Any],
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
    strict: bool,
) -> None:
    for index, item in enumerate(career_history):
        path = f"career_history[{index}]"
        if not isinstance(item, dict):
            errors.append(_issue(path, "career item must be an object", "error"))
            continue
        _check_required(item, REQUIRED_CAREER_FIELDS, path, errors)
        duration = item.get("duration_months")
        if duration is not None and (
            not isinstance(duration, int) or isinstance(duration, bool) or duration < 0
        ):
            (errors if strict else warnings).append(
                _issue(
                    f"{path}.duration_months",
                    "duration_months should be an integer >= 0",
                    "error" if strict else "warning",
                )
            )
        description = item.get("description")
        if isinstance(description, str) and not description.strip():
            warnings.append(_issue(f"{path}.description", "career description is empty", "warning"))


def _validate_skills(
    skills: list[Any],
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
    strict: bool,
) -> None:
    for index, item in enumerate(skills):
        path = f"skills[{index}]"
        if not isinstance(item, dict):
            errors.append(_issue(path, "skill item must be an object", "error"))
            continue
        _check_required(item, REQUIRED_SKILL_FIELDS, path, errors)

        proficiency = item.get("proficiency")
        if proficiency is not None and proficiency not in VALID_SKILL_PROFICIENCIES:
            (errors if strict else warnings).append(
                _issue(
                    f"{path}.proficiency",
                    "proficiency should be beginner/intermediate/advanced/expert",
                    "error" if strict else "warning",
                )
            )

        endorsements = item.get("endorsements")
        if endorsements is not None and (
            not isinstance(endorsements, int) or isinstance(endorsements, bool) or endorsements < 0
        ):
            (errors if strict else warnings).append(
                _issue(
                    f"{path}.endorsements",
                    "endorsements should be an integer >= 0",
                    "error" if strict else "warning",
                )
            )

        duration = item.get("duration_months")
        if proficiency == "expert" and duration == 0:
            warnings.append(
                _issue(f"{path}.duration_months", "expert skill has zero recorded duration", "warning")
            )


def _validate_redrob_signals(
    redrob: dict[str, Any],
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
    strict: bool,
) -> None:
    severity = "error" if strict else "warning"
    issue_target = errors if strict else warnings
    _check_number_range(
        redrob.get("recruiter_response_rate"),
        "redrob_signals.recruiter_response_rate",
        0,
        1,
        issue_target,
        severity,
    )
    _check_number_range(
        redrob.get("interview_completion_rate"),
        "redrob_signals.interview_completion_rate",
        0,
        1,
        issue_target,
        severity,
    )
    _check_number_range(
        redrob.get("offer_acceptance_rate"),
        "redrob_signals.offer_acceptance_rate",
        -1,
        1,
        issue_target,
        severity,
    )
    _check_number_range(
        redrob.get("notice_period_days"),
        "redrob_signals.notice_period_days",
        0,
        180,
        issue_target,
        severity,
    )

    completeness = redrob.get("profile_completeness_score")
    if isinstance(completeness, (int, float)) and completeness < 20:
        warnings.append(
            _issue("redrob_signals.profile_completeness_score", "profile completeness is below 20", "warning")
        )

    salary = redrob.get("expected_salary_range_inr_lpa")
    if isinstance(salary, dict):
        if "min" not in salary or "max" not in salary:
            errors.append(
                _issue("redrob_signals.expected_salary_range_inr_lpa", "salary range should include min and max", "error")
            )
        else:
            minimum = salary.get("min")
            maximum = salary.get("max")
            if _is_number(minimum) and _is_number(maximum) and minimum > maximum:
                warnings.append(
                    _issue("redrob_signals.expected_salary_range_inr_lpa", "salary min is greater than max", "warning")
                )
    elif salary is not None:
        errors.append(
            _issue("redrob_signals.expected_salary_range_inr_lpa", "salary range must be an object", "error")
        )

    signup_date = _parse_date(redrob.get("signup_date"))
    last_active_date = _parse_date(redrob.get("last_active_date"))
    if signup_date and last_active_date and last_active_date < signup_date:
        warnings.append(
            _issue("redrob_signals.last_active_date", "last_active_date is earlier than signup_date", "warning")
        )


def _check_required(
    source: dict[str, Any],
    required_fields: list[str],
    path_prefix: str,
    errors: list[ValidationIssue],
) -> None:
    for field in required_fields:
        if field not in source:
            path = f"{path_prefix}.{field}" if path_prefix else field
            errors.append(_issue(path, "required field is missing", "error"))


def _check_number_range(
    value: Any,
    path: str,
    minimum: float,
    maximum: float,
    issues: list[ValidationIssue],
    severity: str = "warning",
) -> None:
    if value is None:
        return
    if not _is_number(value) or not minimum <= value <= maximum:
        issues.append(_issue(path, f"value should be between {minimum:g} and {maximum:g}", severity))


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _skill_names(skills: list[Any]) -> list[str]:
    names: list[str] = []
    for skill in skills:
        if isinstance(skill, dict) and skill.get("name"):
            names.append(str(skill["name"]))
        elif isinstance(skill, str):
            names.append(skill)
    return names


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _issue(path: str, message: str, severity: str) -> ValidationIssue:
    return ValidationIssue(path=path, message=message, severity=severity)
