from __future__ import annotations

from src.scoring_config import (
    FEATURE_WEIGHTS_DRAFT,
    get_experience_band,
    scoring_config_to_markdown,
    validate_feature_weights,
)


def test_validate_feature_weights_returns_true_for_draft_weights():
    assert validate_feature_weights(FEATURE_WEIGHTS_DRAFT)


def test_get_experience_band_for_ideal():
    assert get_experience_band(6.5)["label"] == "ideal"


def test_get_experience_band_for_too_junior():
    assert get_experience_band(2.5)["label"] == "too_junior"


def test_get_experience_band_for_too_senior():
    assert get_experience_band(12.0)["label"] == "too_senior"


def test_get_experience_band_for_unknown():
    assert get_experience_band(None)["label"] == "unknown"


def test_scoring_config_to_markdown_contains_career_evidence():
    assert "career_evidence" in scoring_config_to_markdown()
