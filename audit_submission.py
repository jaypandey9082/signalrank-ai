from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from generate_submission import _find_external_validator
from src.export import compare_csv_xlsx, read_submission_csv
from src.repo_audit import format_repo_audit_markdown, run_repo_audit
from src.submission_validator import format_submission_validation_markdown, validate_submission_file
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit final SignalRank AI submission artifacts.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--xlsx")
    parser.add_argument("--candidates")
    parser.add_argument("--report-out", default="outputs/submission_audit.md")
    parser.add_argument("--top100-out", default="outputs/top100_review.md")
    parser.add_argument("--skip-external-validator", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    validation = validate_submission_file(args.csv, expected_count=100)
    parity = compare_csv_xlsx(args.csv, args.xlsx) if args.xlsx else None
    repo_report = run_repo_audit(".")
    external = ""
    if not args.skip_external_validator:
        external = _run_external_validator(args.csv)

    write_top100_review(args.csv, args.top100_out)
    markdown = build_audit_markdown(validation, parity, repo_report, external, args)
    ensure_parent_dir(args.report_out)
    Path(args.report_out).write_text(markdown, encoding="utf-8")
    print(f"Wrote audit report to {args.report_out}")
    print(f"Wrote top-100 review to {args.top100_out}")

    passed = validation.is_valid and repo_report.passed and (parity is None or parity["passed"])
    if external and "failed" in external.lower():
        passed = False
    return 0 if passed else 1


def build_audit_markdown(validation, parity, repo_report, external: str, args: argparse.Namespace) -> str:
    lines = [
        "# Final Submission Audit",
        "",
        f"- CSV: `{args.csv}`",
        f"- XLSX: `{args.xlsx}`" if args.xlsx else "- XLSX: not provided",
        f"- Candidates: `{args.candidates}`" if args.candidates else "- Candidates: not provided",
        "",
        "## Internal Validation",
        "",
        format_submission_validation_markdown(validation).strip(),
    ]
    if parity is not None:
        lines.extend(
            [
                "",
                "## CSV/XLSX Parity",
                "",
                f"- Passed: {parity['passed']}",
                f"- CSV rows: {parity['csv_row_count']}",
                f"- XLSX rows: {parity['xlsx_row_count']}",
                f"- Columns match: {parity['columns_match']}",
            ]
        )
        if parity["issues"]:
            lines.extend(f"- {issue}" for issue in parity["issues"])
    lines.extend(["", "## Repo Audit", "", format_repo_audit_markdown(repo_report).strip()])
    if external:
        lines.extend(["", "## External Validator", "", "```text", external.strip(), "```"])
    return "\n".join(lines) + "\n"


def write_top100_review(csv_path: str | Path, out_path: str | Path) -> None:
    rows = read_submission_csv(csv_path)
    lines = ["# Top 100 Review", "", "| Rank | Candidate | Score | Reasoning |", "| ---: | --- | ---: | --- |"]
    for row in rows:
        reasoning = str(row.get("reasoning", "")).replace("|", "\\|")
        lines.append(f"| {row.get('rank', '')} | {row.get('candidate_id', '')} | {row.get('score', '')} | {reasoning} |")
    ensure_parent_dir(out_path)
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_external_validator(csv_path: str | Path) -> str:
    validator = _find_external_validator()
    if validator is None:
        return "External validate_submission.py not found; skipped."
    completed = subprocess.run([sys.executable, str(validator), str(csv_path)], check=False, capture_output=True, text=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    return "External validator passed:\n" + output if completed.returncode == 0 else "External validator failed:\n" + output


if __name__ == "__main__":
    raise SystemExit(main())
