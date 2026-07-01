from __future__ import annotations

import json
import subprocess
import sys

from src.export import compare_csv_xlsx, read_submission_csv, write_submission_xlsx
from src.submission import SubmissionRow
from src.submission_validator import validate_submission_file
from tests.test_scoring import make_keyword_stuffer, make_strong_candidate


def test_rank_py_csv_only_path_does_not_require_xlsx_or_report(tmp_path):
    candidates = tmp_path / "candidates.json"
    out = tmp_path / "submission.csv"
    report = tmp_path / "submission_run_report.md"
    _write_three_candidates(candidates)

    completed = subprocess.run(
        [
            sys.executable,
            "rank.py",
            "--candidates",
            str(candidates),
            "--out",
            str(out),
            "--top-k",
            "3",
            "--allow-partial",
        ],
        cwd="/Users/jaypandey/Documents/SignalRank AI",
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert out.exists()
    assert not report.exists()
    assert validate_submission_file(out, expected_count=3).is_valid


def test_repeated_tiny_fast_runs_are_deterministic(tmp_path):
    candidates = tmp_path / "candidates.json"
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_three_candidates(candidates)

    for out in [first, second]:
        completed = subprocess.run(
            [
                sys.executable,
                "rank.py",
                "--candidates",
                str(candidates),
                "--out",
                str(out),
                "--top-k",
                "3",
                "--allow-partial",
            ],
            cwd="/Users/jaypandey/Documents/SignalRank AI",
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_csv_xlsx_parity_check_works_on_tiny_outputs(tmp_path):
    csv_path = tmp_path / "submission.csv"
    xlsx_path = tmp_path / "submission.xlsx"
    rows = [
        SubmissionRow("CAND_0000001", 1, 0.9, "Strong fit with ranking evidence."),
        SubmissionRow("CAND_0000002", 2, 0.8, "Relevant evidence with availability."),
    ]
    csv_path.write_text(
        "candidate_id,rank,score,reasoning\n"
        "CAND_0000001,1,0.9,Strong fit with ranking evidence.\n"
        "CAND_0000002,2,0.8,Relevant evidence with availability.\n",
        encoding="utf-8",
    )
    write_submission_xlsx(rows, xlsx_path)

    parity = compare_csv_xlsx(csv_path, xlsx_path)

    assert parity["passed"]
    assert len(read_submission_csv(csv_path)) == 2


def _write_three_candidates(path):
    candidates = [make_strong_candidate(), make_keyword_stuffer(), make_strong_candidate()]
    candidates[2]["candidate_id"] = "CAND_0000103"
    path.write_text(json.dumps(candidates), encoding="utf-8")
