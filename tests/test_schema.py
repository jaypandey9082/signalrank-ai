from __future__ import annotations

from copy import deepcopy

from src.schema import candidate_brief, validate_candidate


def make_candidate() -> dict:
    return {
        "candidate_id": "CAND_0000001",
        "profile": {
            "anonymized_name": "Candidate One",
            "headline": "Senior ML engineer",
            "summary": "Builds search and recommendation systems.",
            "location": "Bengaluru",
            "country": "India",
            "years_of_experience": 8,
            "current_title": "Senior Machine Learning Engineer",
            "current_company": "SearchWorks",
            "current_company_size": "201-500",
            "current_industry": "Internet",
        },
        "career_history": [
            {
                "company": "SearchWorks",
                "title": "Senior Machine Learning Engineer",
                "start_date": "2021-01-01",
                "end_date": None,
                "duration_months": 42,
                "is_current": True,
                "industry": "Internet",
                "company_size": "201-500",
                "description": "Owned ranking and retrieval pipelines.",
            }
        ],
        "education": [
            {
                "institution": "NIT",
                "degree": "M.Tech",
                "field_of_study": "Computer Science",
                "start_year": 2015,
                "end_year": 2017,
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "expert", "endorsements": 40, "duration_months": 96},
            {
                "name": "Learning to Rank",
                "proficiency": "advanced",
                "endorsements": 20,
                "duration_months": 48,
            },
        ],
        "redrob_signals": {
            "profile_completeness_score": 90,
            "signup_date": "2025-10-01",
            "last_active_date": "2026-05-01",
            "open_to_work_flag": True,
            "profile_views_received_30d": 120,
            "applications_submitted_30d": 2,
            "recruiter_response_rate": 0.8,
            "avg_response_time_hours": 12,
            "skill_assessment_scores": {"Python": 90},
            "connection_count": 250,
            "endorsements_received": 50,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 35, "max": 50},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 80,
            "search_appearance_30d": 200,
            "saved_by_recruiters_30d": 10,
            "interview_completion_rate": 0.9,
            "offer_acceptance_rate": 0.6,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }


def test_valid_sample_candidate_passes():
    result = validate_candidate(make_candidate())

    assert result.is_valid
    assert result.errors == []


def test_bad_candidate_id_fails():
    candidate = make_candidate()
    candidate["candidate_id"] = "BAD_1"

    result = validate_candidate(candidate)

    assert not result.is_valid
    assert any(issue.path == "candidate_id" for issue in result.errors)


def test_missing_profile_fails():
    candidate = make_candidate()
    del candidate["profile"]

    result = validate_candidate(candidate)

    assert not result.is_valid
    assert any(issue.path == "profile" for issue in result.errors)


def test_missing_required_profile_field_fails():
    candidate = make_candidate()
    del candidate["profile"]["headline"]

    result = validate_candidate(candidate)

    assert not result.is_valid
    assert any(issue.path == "profile.headline" for issue in result.errors)


def test_salary_min_greater_than_max_produces_warning():
    candidate = make_candidate()
    candidate["redrob_signals"]["expected_salary_range_inr_lpa"] = {"min": 60, "max": 40}

    result = validate_candidate(candidate)

    assert result.is_valid
    assert any("salary min" in issue.message for issue in result.warnings)


def test_expert_skill_with_zero_duration_produces_warning():
    candidate = make_candidate()
    candidate["skills"][0]["duration_months"] = 0

    result = validate_candidate(candidate)

    assert result.is_valid
    assert any("expert skill" in issue.message for issue in result.warnings)


def test_candidate_brief_does_not_crash_on_partial_candidate():
    brief = candidate_brief({"candidate_id": "CAND_0000001", "profile": {"current_title": "Engineer"}})

    assert brief["candidate_id"] == "CAND_0000001"
    assert brief["current_title"] == "Engineer"
    assert brief["validation_status"] == "invalid"


def test_strict_mode_can_turn_range_problem_into_invalid_candidate():
    candidate = deepcopy(make_candidate())
    candidate["redrob_signals"]["recruiter_response_rate"] = 1.5

    result = validate_candidate(candidate, strict=True)

    assert not result.is_valid
