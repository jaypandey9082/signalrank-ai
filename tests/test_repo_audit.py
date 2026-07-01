from __future__ import annotations

from src.repo_audit import check_forbidden_dependencies, check_gitignore, check_submission_metadata, run_repo_audit


def test_forbidden_dependency_detection_works(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pytest\nopenai>=1.0\n", encoding="utf-8")

    issues = check_forbidden_dependencies(requirements)

    assert any(issue.code == "forbidden_dependency" for issue in issues)


def test_gitignore_check_works(tmp_path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(
        "\n".join(["candidates.jsonl", "candidates.jsonl.gz", "outputs/submission.csv", "outputs/submission.xlsx"]),
        encoding="utf-8",
    )

    assert check_gitignore(gitignore) == []


def test_tracked_file_check_handles_empty_git_output_safely(tmp_path):
    _write_clean_repo_files(tmp_path)

    report = run_repo_audit(tmp_path)

    assert not any(issue.code == "protected_file_tracked" for issue in report.issues)


def test_metadata_check_warns_for_placeholders_but_does_not_fail(tmp_path):
    _write_clean_repo_files(tmp_path)

    issues = check_submission_metadata(tmp_path / "submission_metadata.yaml", tmp_path)

    assert any(issue.code == "metadata_placeholder" for issue in issues)
    assert not any(issue.severity == "error" for issue in issues)


def _write_clean_repo_files(root):
    (root / ".gitignore").write_text(
        "\n".join(["candidates.jsonl", "candidates.jsonl.gz", "outputs/submission.csv", "outputs/submission.xlsx"]),
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (root / "submission_metadata.yaml").write_text(
        """
team_name: "YOUR_TEAM_NAME"
primary_contact:
  name: "YOUR_NAME"
  email: "YOUR_EMAIL"
  phone: "YOUR_PHONE"
reproduce_command: "python rank.py --candidates ./candidates.jsonl --out ./submission.csv"
declarations:
  reproduction_tested: false
  has_network_during_ranking: false
  uses_gpu_for_inference: false
ai_tools_used:
  - "Codex"
ai_usage_summary: "Used for code assistance only."
""".strip()
        + "\n",
        encoding="utf-8",
    )
