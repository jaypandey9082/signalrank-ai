from __future__ import annotations

from src.ui_components import cap_top_k_for_demo, render_status_chip, score_badge


def test_cap_top_k_for_demo_keeps_valid_selection():
    effective, warning = cap_top_k_for_demo(3, 8)

    assert effective == 3
    assert warning is None


def test_cap_top_k_for_demo_caps_to_loaded_count():
    effective, warning = cap_top_k_for_demo(10, 8)

    assert effective == 8
    assert warning == "Only 8 candidates loaded, so Top K was capped to 8 for this demo."


def test_score_badge_returns_expected_bands():
    assert "elite" in score_badge(0.91)
    assert "strong" in score_badge(0.73)
    assert "good" in score_badge(0.61)
    assert "borderline" in score_badge(0.50)
    assert "weak" in score_badge(0.21)


def test_status_chip_escapes_label_and_defaults_unknown_kind():
    chip = render_status_chip("<script>alert(1)</script>", "unknown")

    assert "&lt;script&gt;" in chip
    assert "sr-chip-neutral" in chip
