from __future__ import annotations

import csv
from pathlib import Path

from scripts.final_gate import check_deck, check_metadata, run_final_gate


def test_final_gate_helper_detects_missing_csv_as_blocker(tmp_path: Path):
    report = run_final_gate(
        candidates_path=None,
        csv_path=tmp_path / "missing.csv",
        xlsx_path=None,
        deck_path=None,
        root=tmp_path,
        skip_runtime_benchmark=True,
        skip_external_validator=True,
        allow_placeholder_metadata=True,
    )

    assert report.status == "BLOCKED"
    assert any(issue.code == "csv_missing" for issue in report.issues)


def test_final_gate_accepts_valid_tiny_rows_with_direct_validator(tmp_path: Path):
    csv_path = tmp_path / "tiny.csv"
    _write_valid_csv(csv_path, count=3)

    from src.submission_validator import validate_submission_file

    report = validate_submission_file(csv_path, expected_count=3)

    assert report.is_valid


def test_metadata_placeholder_detection_blocks_by_default(tmp_path: Path):
    metadata = tmp_path / "submission_metadata.yaml"
    metadata.write_text(
        "\n".join(
            [
                'team_name: "TODO"',
                'reproduce_command: "python rank.py --candidates ./candidates.jsonl --out ./submission.csv"',
                "methodology_summary: deterministic ranking",
                "has_network_during_ranking: false",
                "uses_gpu_for_inference: false",
                "ai_tools_used:",
                "  - Codex",
                "ai_usage_summary: implementation support",
            ]
        ),
        encoding="utf-8",
    )

    issues = check_metadata(metadata)

    assert any(issue.code == "metadata_placeholders" for issue in issues)


def test_deck_size_check_accepts_small_fake_pdf(tmp_path: Path):
    deck = tmp_path / "deck.pdf"
    deck.write_bytes(b"%PDF-1.4\n%fake\n")

    issues = check_deck(deck)

    assert issues == []


def test_runtime_check_can_be_skipped_safely(tmp_path: Path):
    csv_path = tmp_path / "submission.csv"
    _write_valid_csv(csv_path, count=100)
    deck = tmp_path / "deck.pdf"
    deck.write_bytes(b"%PDF-1.4\n%fake\n")
    (tmp_path / "submission_metadata.yaml").write_text(
        "\n".join(
            [
                'reproduce_command: "python rank.py --candidates ./candidates.jsonl --out ./submission.csv"',
                "methodology_summary: deterministic ranking",
                "has_network_during_ranking: false",
                "uses_gpu_for_inference: false",
                "ai_tools_used:",
                "  - Codex",
                "ai_usage_summary: implementation support",
            ]
        ),
        encoding="utf-8",
    )

    report = run_final_gate(
        candidates_path=None,
        csv_path=csv_path,
        xlsx_path=None,
        deck_path=deck,
        root=tmp_path,
        skip_runtime_benchmark=True,
        skip_external_validator=True,
    )

    assert any(issue.code == "runtime_benchmark_skipped" for issue in report.issues)


def _write_valid_csv(path: Path, count: int) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        for index in range(1, count + 1):
            writer.writerow(
                {
                    "candidate_id": f"CAND_{index:07d}",
                    "rank": index,
                    "score": f"{1 - index / 1000:.6f}",
                    "reasoning": f"Candidate has {index} years engineer experience with ranking search production evidence.",
                }
            )
