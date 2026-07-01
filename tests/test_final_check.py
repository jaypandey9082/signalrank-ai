from __future__ import annotations

from scripts.final_check import run_final_checks


def test_final_check_detects_required_docs_in_project_like_folder(tmp_path):
    _write_minimal_project(tmp_path)

    checks = run_final_checks(tmp_path, skip_validator=True, skip_audit=True)

    failed = [check for check in checks if not check.passed]
    assert not failed


def test_final_check_fails_when_required_critical_files_missing(tmp_path):
    (tmp_path / ".gitignore").write_text("", encoding="utf-8")

    checks = run_final_checks(tmp_path, skip_validator=True, skip_audit=True)

    assert any(not check.passed and check.code == "required_file" for check in checks)


def test_final_check_does_not_require_full_candidates_for_unit_tests(tmp_path):
    _write_minimal_project(tmp_path)

    checks = run_final_checks(tmp_path, csv_path=None, xlsx_path=None, candidates_path=None, skip_validator=True, skip_audit=True)

    assert all(check.code != "candidates_exists" for check in checks)


def _write_minimal_project(root):
    for rel_path in [
        "README.md",
        "submission_metadata.yaml",
        "FINAL_SUBMISSION_CHECKLIST.md",
        "SUBMISSION_PACKET.md",
        "DEPLOYMENT.md",
        "DEMO_SCRIPT.md",
        "deck/approach_deck.md",
        "deck/approach_deck.html",
        "sandbox/app.py",
    ]:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")
    (root / "requirements.txt").write_text("streamlit\npytest\n", encoding="utf-8")
    (root / ".gitignore").write_text(
        "\n".join(["candidates.jsonl", "candidates.jsonl.gz", "outputs/submission.csv", "outputs/submission.xlsx"]),
        encoding="utf-8",
    )
