from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


FORBIDDEN_PACKAGES = (
    "openai",
    "anthropic",
    "google-generativeai",
    "langchain",
    "torch",
    "tensorflow",
    "sentence-transformers",
    "transformers",
    "cohere",
)
FORBIDDEN_RANKING_IMPORTS = (
    "requests",
    "urllib.request",
    "socket",
    "openai",
    "anthropic",
    "google.generativeai",
)
SECRET_MARKERS = (
    "OPENAI" + "_API_KEY",
    "ANTHROPIC" + "_API_KEY",
    "GEMINI" + "_API_KEY",
)
MUST_IGNORE = (
    "candidates.jsonl",
    "candidates.jsonl.gz",
    "outputs/submission.csv",
    "outputs/submission.xlsx",
)
PROTECTED_TRACKED_FILES = (
    "candidates.jsonl",
    "candidates.jsonl.gz",
    "outputs/submission.csv",
    "outputs/submission.xlsx",
    "submission.csv",
    "submission.xlsx",
)
RANKING_PATH_FILES = (
    "rank.py",
    "generate_submission.py",
    "src/submission.py",
    "src/ranking.py",
    "src/combined_scoring.py",
    "src/features.py",
    "src/scoring.py",
    "src/redrob_scoring.py",
    "src/trap_penalties.py",
    "src/reasoning.py",
    "src/export.py",
)


@dataclass
class RepoAuditIssue:
    severity: str
    code: str
    message: str


@dataclass
class RepoAuditReport:
    passed: bool
    issues: list[RepoAuditIssue]


def run_repo_audit(root: str | Path = ".") -> RepoAuditReport:
    root_path = Path(root)
    issues: list[RepoAuditIssue] = []
    tracked = _git_ls_files(root_path)
    issues.extend(_check_protected_tracked(tracked))
    issues.extend(_check_large_tracked(root_path, tracked))
    issues.extend(check_forbidden_dependencies(root_path / "requirements.txt"))
    issues.extend(_check_forbidden_imports(root_path))
    issues.extend(_check_secret_markers(root_path, tracked))
    issues.extend(check_gitignore(root_path / ".gitignore"))
    issues.extend(check_submission_metadata(root_path / "submission_metadata.yaml", root_path))
    errors = [issue for issue in issues if issue.severity == "error"]
    return RepoAuditReport(passed=not errors, issues=issues)


def check_forbidden_dependencies(requirements_path: str | Path) -> list[RepoAuditIssue]:
    path = Path(requirements_path)
    if not path.exists():
        return [RepoAuditIssue("warning", "requirements_missing", "requirements.txt is missing.")]
    text = path.read_text(encoding="utf-8").lower()
    issues = []
    for package in FORBIDDEN_PACKAGES:
        pattern = re.compile(rf"^\s*{re.escape(package)}(?:[<>=~! ]|$)", re.MULTILINE)
        if pattern.search(text):
            issues.append(RepoAuditIssue("error", "forbidden_dependency", f"Forbidden dependency listed: {package}."))
    return issues


def check_gitignore(path: str | Path) -> list[RepoAuditIssue]:
    gitignore = Path(path)
    if not gitignore.exists():
        return [RepoAuditIssue("error", "gitignore_missing", ".gitignore is missing.")]
    lines = {line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()}
    return [
        RepoAuditIssue("error", "gitignore_missing_entry", f".gitignore missing {entry}.")
        for entry in MUST_IGNORE
        if entry not in lines
    ]


def check_submission_metadata(
    path: str | Path = "submission_metadata.yaml",
    root: str | Path = ".",
) -> list[RepoAuditIssue]:
    metadata = Path(path)
    root_path = Path(root)
    if not metadata.exists():
        return [RepoAuditIssue("error", "metadata_missing", "submission_metadata.yaml is missing.")]
    text = metadata.read_text(encoding="utf-8")
    issues: list[RepoAuditIssue] = []
    _require_text(text, "reproduce_command:", "metadata_missing_reproduce_command", issues)
    if "reproduce_command:" in text and "rank.py" not in _metadata_value(text, "reproduce_command"):
        issues.append(RepoAuditIssue("error", "metadata_reproduce_not_rank", "reproduce_command must use rank.py."))
    if "reproduce_command:" in text and "--out" not in _metadata_value(text, "reproduce_command"):
        issues.append(RepoAuditIssue("error", "metadata_reproduce_no_csv", "reproduce_command must produce a CSV via --out."))
    if re.search(r"reproduction_tested:\s*true", text, flags=re.IGNORECASE):
        full_report = root_path / "outputs" / "benchmark_report.md"
        if not full_report.exists() or "Total runtime" not in full_report.read_text(encoding="utf-8", errors="ignore"):
            issues.append(
                RepoAuditIssue(
                    "error",
                    "metadata_reproduction_claim_unproven",
                    "reproduction_tested is true without a successful full benchmark report.",
                )
            )
    for placeholder in ("YOUR_TEAM_NAME", "YOUR_NAME", "YOUR_EMAIL", "YOUR_PHONE"):
        if placeholder in text:
            issues.append(RepoAuditIssue("warning", "metadata_placeholder", f"Placeholder still present: {placeholder}."))
    _require_text(text, "ai_tools_used:", "metadata_missing_ai_tools_used", issues)
    _require_text(text, "ai_usage_summary:", "metadata_missing_ai_usage_summary", issues)
    if not re.search(r"has_network_during_ranking:\s*false", text, flags=re.IGNORECASE):
        issues.append(RepoAuditIssue("error", "metadata_network_flag", "has_network_during_ranking must be false."))
    if not re.search(r"uses_gpu_for_inference:\s*false", text, flags=re.IGNORECASE):
        issues.append(RepoAuditIssue("error", "metadata_gpu_flag", "uses_gpu_for_inference must be false."))
    return issues


def format_repo_audit_markdown(report: RepoAuditReport) -> str:
    lines = ["# Submission Audit", "", f"- Passed: {report.passed}", f"- Issue count: {len(report.issues)}"]
    if report.issues:
        lines.extend(["", "## Issues"])
        lines.extend(f"- `{issue.severity}` `{issue.code}`: {issue.message}" for issue in report.issues)
    return "\n".join(lines) + "\n"


def _git_ls_files(root: Path) -> list[str]:
    try:
        completed = subprocess.run(["git", "ls-files"], cwd=root, check=False, capture_output=True, text=True)
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _check_protected_tracked(tracked: list[str]) -> list[RepoAuditIssue]:
    tracked_set = set(tracked)
    return [
        RepoAuditIssue("error", "protected_file_tracked", f"{path} must not be tracked by git.")
        for path in PROTECTED_TRACKED_FILES
        if path in tracked_set
    ]


def _check_large_tracked(root: Path, tracked: list[str]) -> list[RepoAuditIssue]:
    issues: list[RepoAuditIssue] = []
    for rel_path in tracked:
        path = root / rel_path
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > 25 * 1024 * 1024:
            issues.append(RepoAuditIssue("error", "large_tracked_file", f"Tracked file exceeds 25 MB: {rel_path}."))
    return issues


def _check_forbidden_imports(root: Path) -> list[RepoAuditIssue]:
    issues: list[RepoAuditIssue] = []
    for rel_path in RANKING_PATH_FILES:
        path = root / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for package in FORBIDDEN_RANKING_IMPORTS:
            if re.search(rf"^\s*(import|from)\s+{re.escape(package)}(?:\s|\.|$)", text, flags=re.MULTILINE):
                issues.append(RepoAuditIssue("error", "forbidden_ranking_import", f"{rel_path} imports {package}."))
    return issues


def _check_secret_markers(root: Path, tracked: list[str]) -> list[RepoAuditIssue]:
    issues: list[RepoAuditIssue] = []
    scan_paths = [root / path for path in tracked if path.endswith((".py", ".md", ".yaml", ".yml", ".txt"))]
    for path in scan_paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in SECRET_MARKERS:
            if marker in text:
                issues.append(RepoAuditIssue("error", "api_key_marker", f"{path.relative_to(root)} contains {marker}."))
    return issues


def _require_text(text: str, needle: str, code: str, issues: list[RepoAuditIssue]) -> None:
    if needle not in text:
        issues.append(RepoAuditIssue("error", code, f"submission_metadata.yaml missing {needle}"))


def _metadata_value(text: str, key: str) -> str:
    match = re.search(rf"^\s*{re.escape(key)}\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")
