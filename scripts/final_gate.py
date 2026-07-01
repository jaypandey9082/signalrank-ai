from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generate_submission import _find_external_validator
from src.export import compare_csv_xlsx, read_submission_csv
from src.repo_audit import run_repo_audit
from src.submission_validator import SubmissionValidationReport, validate_submission_file
from src.utils import ensure_parent_dir


FIVE_MINUTES_SECONDS = 300.0
REQUIRED_METADATA_FIELDS = (
    "reproduce_command:",
    "methodology_summary:",
    "ai_tools_used:",
    "ai_usage_summary:",
)
PLACEHOLDER_MARKERS = (
    "TODO",
    "YOUR_",
    "your team",
    "your email",
    "your phone",
    "USERNAME",
    "YOUR_STREAMLIT_APP_URL",
)
PORTAL_PLACEHOLDERS = {"", "TODO", "TBD", "N/A", "NA", "NONE"}


@dataclass
class GateIssue:
    severity: str
    code: str
    message: str
    evidence: str = ""


@dataclass
class RuntimeCheckResult:
    status: str
    elapsed_seconds: float | None
    output_path: str | None
    output_hash: str | None
    matches_reference: bool | None
    first_difference: str
    message: str


@dataclass
class DeterminismCheckResult:
    status: str
    hash_a: str | None
    hash_b: str | None
    same_hash: bool | None
    message: str


@dataclass
class GateReport:
    status: str
    issues: list[GateIssue]
    validation: SubmissionValidationReport | None
    xlsx_parity: dict[str, Any] | None
    runtime: RuntimeCheckResult | None
    determinism: DeterminismCheckResult | None
    external_validator_output: str
    repo_issue_count: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run strict final upload gate for SignalRank AI.")
    parser.add_argument("--candidates")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--xlsx")
    parser.add_argument("--deck")
    parser.add_argument("--report-out", default="outputs/final_gate_report.md")
    parser.add_argument("--skip-runtime-benchmark", action="store_true")
    parser.add_argument("--skip-external-validator", action="store_true")
    parser.add_argument("--allow-placeholder-metadata", action="store_true")
    return parser


def run_final_gate(
    *,
    candidates_path: str | Path | None,
    csv_path: str | Path,
    xlsx_path: str | Path | None,
    deck_path: str | Path | None,
    root: str | Path = ROOT,
    skip_runtime_benchmark: bool = False,
    skip_external_validator: bool = False,
    allow_placeholder_metadata: bool = False,
) -> GateReport:
    root_path = Path(root)
    issues: list[GateIssue] = []
    validation: SubmissionValidationReport | None = None
    xlsx_parity: dict[str, Any] | None = None
    runtime: RuntimeCheckResult | None = None
    determinism: DeterminismCheckResult | None = None
    external_output = ""

    resolved_csv = resolve_path(root_path, csv_path)
    if not resolved_csv.exists():
        issues.append(GateIssue("blocker", "csv_missing", f"CSV is missing: {resolved_csv}"))
    else:
        validation = validate_submission_file(resolved_csv, expected_count=100)
        if not validation.is_valid:
            issues.append(
                GateIssue(
                    "blocker",
                    "csv_invalid",
                    f"CSV internal validation failed with {validation.error_count} errors.",
                    evidence=f"{validation.warning_count} warnings",
                )
            )
        issues.extend(check_score_spread(resolved_csv))

    if xlsx_path:
        resolved_xlsx = resolve_path(root_path, xlsx_path)
        if not resolved_xlsx.exists():
            issues.append(GateIssue("blocker", "xlsx_missing", f"XLSX is missing: {resolved_xlsx}"))
        elif resolved_csv.exists():
            xlsx_parity = compare_csv_xlsx(resolved_csv, resolved_xlsx)
            if not xlsx_parity["passed"]:
                issues.append(
                    GateIssue(
                        "blocker",
                        "xlsx_parity_failed",
                        "XLSX does not match CSV exactly.",
                        evidence="; ".join(xlsx_parity["issues"][:5]),
                    )
                )
    else:
        issues.append(GateIssue("warning", "xlsx_not_provided", "XLSX path was not provided."))

    if deck_path:
        issues.extend(check_deck(resolve_path(root_path, deck_path)))
    else:
        issues.append(GateIssue("blocker", "deck_not_provided", "Deck PDF path was not provided."))

    issues.extend(check_metadata(root_path / "submission_metadata.yaml", allow_placeholders=allow_placeholder_metadata))
    issues.extend(check_repo_hygiene(root_path))
    issues.extend(check_sandbox_assets(root_path))

    if candidates_path:
        resolved_candidates = resolve_path(root_path, candidates_path)
        issues.extend(check_candidates_file(resolved_candidates, resolved_csv if resolved_csv.exists() else None))
    else:
        issues.append(GateIssue("blocker", "candidates_not_provided", "Candidates path is required for final runtime gate."))

    if not skip_external_validator and resolved_csv.exists():
        external_output = run_external_validator(resolved_csv)
        if external_output.startswith("External validator failed") or external_output.startswith("External validator could not run"):
            issues.append(GateIssue("blocker", "external_validator_failed", "External validator failed.", external_output[:500]))
        elif "not found" in external_output.lower():
            issues.append(GateIssue("warning", "external_validator_missing", "External validate_submission.py was not found."))
    elif skip_external_validator:
        issues.append(GateIssue("warning", "external_validator_skipped", "External validator was skipped by flag."))

    if skip_runtime_benchmark:
        issues.append(GateIssue("warning", "runtime_benchmark_skipped", "Runtime benchmark was skipped by flag."))
    elif candidates_path and resolved_csv.exists():
        runtime = run_runtime_check(resolve_path(root_path, candidates_path), resolved_csv, root_path)
        if runtime.status == "BLOCKER":
            issues.append(GateIssue("blocker", "runtime_check_failed", runtime.message, runtime.first_difference))
        elif runtime.status == "WARN":
            issues.append(GateIssue("warning", "runtime_check_warning", runtime.message, runtime.first_difference))

        determinism = run_determinism_check(resolve_path(root_path, candidates_path), root_path)
        if determinism.status == "BLOCKER":
            issues.append(GateIssue("blocker", "determinism_failed", determinism.message))
        elif determinism.status == "WARN":
            issues.append(GateIssue("warning", "determinism_warning", determinism.message))

    blockers = [issue for issue in issues if issue.severity == "blocker"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    status = "BLOCKED" if blockers else "WARN" if warnings else "PASS"
    repo_issue_count = sum(1 for issue in issues if issue.code.startswith("repo_"))
    return GateReport(status, issues, validation, xlsx_parity, runtime, determinism, external_output, repo_issue_count)


def check_score_spread(csv_path: str | Path) -> list[GateIssue]:
    try:
        rows = read_submission_csv(csv_path)
    except OSError as exc:
        return [GateIssue("blocker", "csv_read_failed", f"Could not read CSV: {exc}")]
    scores: list[float] = []
    for row in rows:
        try:
            scores.append(float(row.get("score", "")))
        except ValueError:
            continue
    if not scores:
        return []
    spread = max(scores) - min(scores)
    issues: list[GateIssue] = []
    if spread == 0:
        issues.append(GateIssue("blocker", "score_no_spread", "All scores are identical."))
    elif spread < 0.01:
        issues.append(GateIssue("warning", "score_low_spread", f"Score spread is narrow: {spread:.6f}."))
    return issues


def check_metadata(path: str | Path, *, allow_placeholders: bool = False) -> list[GateIssue]:
    metadata = Path(path)
    if not metadata.exists():
        return [GateIssue("blocker", "metadata_missing", "submission_metadata.yaml is missing.")]
    text = metadata.read_text(encoding="utf-8")
    lower = text.lower()
    issues: list[GateIssue] = []
    for field in REQUIRED_METADATA_FIELDS:
        if field not in text:
            issues.append(GateIssue("blocker", "metadata_missing_field", f"Metadata missing {field}"))
    reproduce = metadata_value(text, "reproduce_command")
    if "rank.py" not in reproduce:
        issues.append(GateIssue("blocker", "metadata_reproduce_not_rank", "reproduce_command must use rank.py."))
    if "has_network_during_ranking:" not in text or "has_network_during_ranking: false" not in lower:
        issues.append(GateIssue("blocker", "metadata_network_flag", "has_network_during_ranking must be false."))
    if "uses_gpu_for_inference:" not in text or "uses_gpu_for_inference: false" not in lower:
        issues.append(GateIssue("blocker", "metadata_gpu_flag", "uses_gpu_for_inference must be false."))
    placeholders = [marker for marker in PLACEHOLDER_MARKERS if marker.lower() in lower]
    if placeholders and not allow_placeholders:
        issues.append(
            GateIssue(
                "blocker",
                "metadata_placeholders",
                "Metadata still contains placeholder values.",
                evidence=", ".join(sorted(set(placeholders))),
            )
        )
    elif placeholders:
        issues.append(GateIssue("warning", "metadata_placeholders_allowed", "Metadata placeholders allowed by flag."))
    return issues


def check_deck(deck_path: str | Path) -> list[GateIssue]:
    path = Path(deck_path)
    if not path.exists():
        return [GateIssue("blocker", "deck_missing", f"Deck PDF is missing: {path}")]
    size = path.stat().st_size
    if size == 0:
        return [GateIssue("blocker", "deck_empty", f"Deck PDF is empty: {path}")]
    if size > 5 * 1024 * 1024:
        return [GateIssue("blocker", "deck_too_large", f"Deck PDF exceeds 5 MB: {size} bytes.")]
    return []


def check_repo_hygiene(root: str | Path) -> list[GateIssue]:
    report = run_repo_audit(root)
    issues: list[GateIssue] = []
    for issue in report.issues:
        severity = "blocker" if issue.severity == "error" else "warning"
        issues.append(GateIssue(severity, f"repo_{issue.code}", issue.message))
    return issues


def check_sandbox_assets(root: str | Path) -> list[GateIssue]:
    root_path = Path(root)
    required = (
        "sandbox/app.py",
        "sandbox/sample_candidates_demo.json",
        "sandbox/README.md",
        "docs/sandbox_demo.md",
        "docs/hosted_demo_guide.md",
    )
    issues = [GateIssue("blocker", "sandbox_missing_file", f"Missing sandbox asset: {path}") for path in required if not (root_path / path).exists()]
    requirements = root_path / "requirements.txt"
    if not requirements.exists() or "streamlit" not in requirements.read_text(encoding="utf-8").lower():
        issues.append(GateIssue("blocker", "sandbox_streamlit_missing", "requirements.txt must include streamlit."))
    return issues


def check_candidates_file(candidates_path: str | Path, csv_path: Path | None) -> list[GateIssue]:
    path = Path(candidates_path)
    if not path.exists():
        return [GateIssue("blocker", "candidates_missing", f"Candidates file does not exist: {path}")]
    issues: list[GateIssue] = []
    top_ids = set()
    if csv_path and csv_path.exists():
        top_ids = {row.get("candidate_id", "") for row in read_submission_csv(csv_path)}
    count = 0
    seen_top_ids: set[str] = set()
    try:
        for record in iter_candidate_records(path):
            count += 1
            candidate_id = str(record.get("candidate_id", ""))
            if candidate_id in top_ids:
                seen_top_ids.add(candidate_id)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [GateIssue("blocker", "candidates_read_failed", f"Could not stream candidates file: {exc}")]
    if path.name in {"candidates.jsonl", "candidates.jsonl.gz"} and count != 100000:
        issues.append(GateIssue("warning", "candidate_count_unexpected", f"Expected 100000 candidates, found {count}."))
    elif count < 100:
        issues.append(GateIssue("warning", "candidate_count_small", f"Candidate file has only {count} records."))
    missing = sorted(top_ids - seen_top_ids)
    if missing:
        issues.append(GateIssue("blocker", "top_ids_missing_from_candidates", f"{len(missing)} submitted IDs missing from candidates file.", ", ".join(missing[:10])))
    return issues


def run_external_validator(csv_path: str | Path) -> str:
    validator = _find_external_validator()
    if validator is None:
        return "External validate_submission.py not found; skipped."
    completed = subprocess.run([sys.executable, str(validator), str(csv_path)], check=False, capture_output=True, text=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode == 0:
        return "External validator passed:\n" + output
    return "External validator failed:\n" + output


def run_runtime_check(candidates_path: str | Path, reference_csv: str | Path, root: str | Path = ROOT) -> RuntimeCheckResult:
    root_path = Path(root)
    output_path = root_path / "outputs/audit_reproduce_submission.csv"
    ensure_parent_dir(output_path)
    command = [sys.executable, "rank.py", "--candidates", str(candidates_path), "--out", str(output_path)]
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=root_path, check=False, capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        return RuntimeCheckResult("BLOCKER", elapsed, str(output_path), None, None, completed.stderr[:500], "Official reproduce command failed.")
    reference_hash = sha256_file(reference_csv)
    output_hash = sha256_file(output_path)
    comparison = compare_csv_files(reference_csv, output_path)
    if elapsed > FIVE_MINUTES_SECONDS:
        return RuntimeCheckResult("BLOCKER", elapsed, str(output_path), output_hash, comparison["same_hash"], comparison["first_difference_summary"], f"Official runtime exceeded 5 minutes: {elapsed:.2f}s.")
    if not comparison["same_hash"]:
        return RuntimeCheckResult("BLOCKER", elapsed, str(output_path), output_hash, False, comparison["first_difference_summary"], "Reproduced CSV differs from provided CSV.")
    return RuntimeCheckResult("PASS", elapsed, str(output_path), output_hash, True, "", f"Official reproduce command passed in {elapsed:.2f}s; reference hash {reference_hash}.")


def run_determinism_check(candidates_path: str | Path, root: str | Path = ROOT) -> DeterminismCheckResult:
    root_path = Path(root)
    out_a = root_path / "outputs/audit_reproduce_submission_a.csv"
    out_b = root_path / "outputs/audit_reproduce_submission_b.csv"
    ensure_parent_dir(out_a)
    commands = [
        [sys.executable, "rank.py", "--candidates", str(candidates_path), "--out", str(out_a)],
        [sys.executable, "rank.py", "--candidates", str(candidates_path), "--out", str(out_b)],
    ]
    for command in commands:
        completed = subprocess.run(command, cwd=root_path, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            return DeterminismCheckResult("BLOCKER", None, None, None, "Determinism reproduce command failed.")
    hash_a = sha256_file(out_a)
    hash_b = sha256_file(out_b)
    if hash_a != hash_b:
        return DeterminismCheckResult("BLOCKER", hash_a, hash_b, False, "Two official reproduce runs produced different hashes.")
    return DeterminismCheckResult("PASS", hash_a, hash_b, True, f"Determinism passed: {hash_a}.")


def compare_csv_files(path_a: str | Path, path_b: str | Path) -> dict[str, Any]:
    rows_a = read_submission_csv(path_a)
    rows_b = read_submission_csv(path_b)
    hash_a = sha256_file(path_a)
    hash_b = sha256_file(path_b)
    first_difference = ""
    if len(rows_a) != len(rows_b):
        first_difference = f"row count differs: {len(rows_a)} != {len(rows_b)}"
    else:
        for index, (row_a, row_b) in enumerate(zip(rows_a, rows_b), start=1):
            if row_a != row_b:
                first_difference = f"first difference at row {index}: {row_a} != {row_b}"
                break
    return {"same_hash": hash_a == hash_b, "hash_a": hash_a, "hash_b": hash_b, "first_difference_summary": first_difference}


def check_portal_packet(
    *,
    github_url: str,
    sandbox_url: str,
    deck_path: str | Path,
    xlsx_path: str | Path,
    csv_path: str | Path,
    root: str | Path = ROOT,
) -> list[GateIssue]:
    root_path = Path(root)
    issues: list[GateIssue] = []
    issues.extend(check_url(github_url, "github_url", "GitHub repo URL"))
    issues.extend(check_url(sandbox_url, "sandbox_url", "Sandbox/demo URL"))
    issues.extend(check_deck(resolve_path(root_path, deck_path)))
    resolved_xlsx = resolve_path(root_path, xlsx_path)
    if not resolved_xlsx.exists() or resolved_xlsx.stat().st_size == 0:
        issues.append(GateIssue("blocker", "xlsx_missing", f"XLSX missing or empty: {resolved_xlsx}"))
    resolved_csv = resolve_path(root_path, csv_path)
    if not resolved_csv.exists():
        issues.append(GateIssue("blocker", "csv_missing", f"CSV missing: {resolved_csv}"))
    else:
        validation = validate_submission_file(resolved_csv, expected_count=100)
        if not validation.is_valid:
            issues.append(GateIssue("blocker", "csv_invalid", f"CSV validation failed with {validation.error_count} errors."))
    return issues


def check_url(value: str, code: str, label: str) -> list[GateIssue]:
    stripped = str(value or "").strip()
    if stripped.upper() in PORTAL_PLACEHOLDERS or "TODO" in stripped.upper() or "YOUR_" in stripped.upper():
        return [GateIssue("blocker", code, f"{label} is still a placeholder.")]
    if not stripped.startswith(("http://", "https://")):
        return [GateIssue("blocker", code, f"{label} must start with http:// or https://.")]
    return []


def format_gate_report_markdown(report: GateReport) -> str:
    lines = [
        "# Final Gate Report",
        "",
        f"- Status: {report.status}",
        f"- Blockers: {sum(1 for issue in report.issues if issue.severity == 'blocker')}",
        f"- Warnings: {sum(1 for issue in report.issues if issue.severity == 'warning')}",
    ]
    if report.validation:
        lines.extend(["", "## CSV Validation", "", f"- Valid: {report.validation.is_valid}", f"- Rows: {report.validation.row_count}", f"- Errors: {report.validation.error_count}", f"- Warnings: {report.validation.warning_count}"])
    if report.xlsx_parity:
        lines.extend(["", "## CSV/XLSX Parity", "", f"- Passed: {report.xlsx_parity['passed']}", f"- CSV rows: {report.xlsx_parity['csv_row_count']}", f"- XLSX rows: {report.xlsx_parity['xlsx_row_count']}"])
    if report.runtime:
        lines.extend(["", "## Runtime", "", f"- Status: {report.runtime.status}", f"- Elapsed seconds: {report.runtime.elapsed_seconds}", f"- Message: {report.runtime.message}"])
    if report.determinism:
        lines.extend(["", "## Determinism", "", f"- Status: {report.determinism.status}", f"- Same hash: {report.determinism.same_hash}", f"- Message: {report.determinism.message}"])
    if report.external_validator_output:
        lines.extend(["", "## External Validator", "", "```text", report.external_validator_output.strip(), "```"])
    if report.issues:
        lines.extend(["", "## Issues", "", "| Severity | Code | Message | Evidence |", "|---|---|---|---|"])
        for issue in report.issues:
            lines.append(f"| {issue.severity} | `{issue.code}` | {escape_md(issue.message)} | {escape_md(issue.evidence)} |")
    return "\n".join(lines) + "\n"


def environment_snapshot(root: str | Path = ROOT) -> dict[str, str]:
    branch = ""
    try:
        completed = subprocess.run(["git", "branch", "--show-current"], cwd=Path(root), check=False, capture_output=True, text=True)
        branch = completed.stdout.strip()
    except OSError:
        branch = ""
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_branch": branch or "unknown",
        "gpu_required": "false",
        "network_required_during_ranking": "false",
    }


def iter_candidate_records(path: Path):
    if path.suffix == ".gz":
        opener = gzip.open
        mode = "rt"
    else:
        opener = open
        mode = "r"
    if path.name.endswith(".json") and not path.name.endswith(".jsonl"):
        with opener(path, mode, encoding="utf-8") as handle:  # type: ignore[arg-type]
            data = json.load(handle)
        if isinstance(data, dict):
            yield data
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item
                else:
                    raise ValueError("JSON candidate list contains a non-object item.")
        else:
            raise ValueError("JSON candidates must be an object or list of objects.")
        return
    with opener(path, mode, encoding="utf-8") as handle:  # type: ignore[arg-type]
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise ValueError("JSONL row is not an object.")
            yield record


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_value(text: str, key: str) -> str:
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.strip().startswith(prefix):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def escape_md(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def main() -> int:
    args = build_parser().parse_args()
    report = run_final_gate(
        candidates_path=args.candidates,
        csv_path=args.csv,
        xlsx_path=args.xlsx,
        deck_path=args.deck,
        skip_runtime_benchmark=args.skip_runtime_benchmark,
        skip_external_validator=args.skip_external_validator,
        allow_placeholder_metadata=args.allow_placeholder_metadata,
    )
    markdown = format_gate_report_markdown(report)
    ensure_parent_dir(args.report_out)
    Path(args.report_out).write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"Wrote final gate report to {args.report_out}")
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
