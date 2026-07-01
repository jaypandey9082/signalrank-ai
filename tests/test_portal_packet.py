from __future__ import annotations

import csv
from pathlib import Path

from scripts.check_portal_packet import portal_packet_markdown
from scripts.final_gate import check_portal_packet, check_url


def test_placeholder_github_url_is_blocker():
    issues = check_url("TODO", "github_url", "GitHub repo URL")

    assert any(issue.severity == "blocker" for issue in issues)


def test_valid_url_shape_passes():
    assert check_url("https://github.com/example/repo", "github_url", "GitHub repo URL") == []


def test_missing_xlsx_is_blocker(tmp_path: Path):
    csv_path = tmp_path / "submission.csv"
    deck = tmp_path / "deck.pdf"
    _write_valid_csv(csv_path)
    deck.write_bytes(b"%PDF-1.4\n%fake\n")

    issues = check_portal_packet(
        github_url="https://github.com/example/repo",
        sandbox_url="https://example.streamlit.app",
        deck_path=deck,
        xlsx_path=tmp_path / "missing.xlsx",
        csv_path=csv_path,
        root=tmp_path,
    )

    assert any(issue.code == "xlsx_missing" for issue in issues)


def test_missing_deck_is_blocker(tmp_path: Path):
    csv_path = tmp_path / "submission.csv"
    xlsx = tmp_path / "submission.xlsx"
    _write_valid_csv(csv_path)
    xlsx.write_bytes(b"not-empty")

    issues = check_portal_packet(
        github_url="https://github.com/example/repo",
        sandbox_url="https://example.streamlit.app",
        deck_path=tmp_path / "missing.pdf",
        xlsx_path=xlsx,
        csv_path=csv_path,
        root=tmp_path,
    )

    assert any(issue.code == "deck_missing" for issue in issues)


def test_report_markdown_contains_portal_packet():
    markdown = portal_packet_markdown(
        github_url="TODO",
        sandbox_url="TODO",
        deck="deck.pdf",
        xlsx="submission.xlsx",
        csv_path="submission.csv",
        issues=[],
    )

    assert "Portal Packet" in markdown


def test_csv_validation_integration_passes_on_temp_valid_csv(tmp_path: Path):
    csv_path = tmp_path / "submission.csv"
    deck = tmp_path / "deck.pdf"
    xlsx = tmp_path / "submission.xlsx"
    _write_valid_csv(csv_path)
    deck.write_bytes(b"%PDF-1.4\n%fake\n")
    xlsx.write_bytes(b"not-empty")

    issues = check_portal_packet(
        github_url="https://github.com/example/repo",
        sandbox_url="https://example.streamlit.app",
        deck_path=deck,
        xlsx_path=xlsx,
        csv_path=csv_path,
        root=tmp_path,
    )

    assert not any(issue.code == "csv_invalid" for issue in issues)


def _write_valid_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        for index in range(1, 101):
            writer.writerow(
                {
                    "candidate_id": f"CAND_{index:07d}",
                    "rank": index,
                    "score": f"{1 - index / 1000:.6f}",
                    "reasoning": f"Candidate has {index} years engineer experience with ranking search production evidence.",
                }
            )
