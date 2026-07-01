from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from src.export import write_debug_csv, write_submission_csv, write_submission_xlsx
from src.runtime_report import build_runtime_report, write_runtime_report
from src.submission import build_submission_rows
from src.submission_validator import (
    format_submission_validation_report,
    validate_submission_rows,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate final SignalRank AI submission files.")
    parser.add_argument("--candidates", required=True, help="Path to candidate JSON/JSONL/JSONL.GZ file.")
    parser.add_argument("--out", required=True, help="Path for final submission CSV.")
    parser.add_argument("--xlsx", help="Optional path for final submission XLSX.")
    parser.add_argument("--report-out", default="outputs/submission_run_report.md", help="Path for markdown run report.")
    parser.add_argument("--debug-csv", help="Optional path for debug submission CSV.")
    parser.add_argument("--top-k", type=int, default=100, help="Submission size. Must be 100 unless --allow-partial.")
    parser.add_argument("--limit", type=int, help="Limit candidate rows. Only allowed with --allow-partial.")
    parser.add_argument("--allow-partial", action="store_true", help="Allow partial/sample submission generation for tests.")
    parser.add_argument("--skip-external-validator", action="store_true", help="Skip bundled validate_submission.py if present.")
    return parser


def run_submission_cli(args: argparse.Namespace) -> int:
    try:
        result = build_submission_rows(
            args.candidates,
            top_k=args.top_k,
            limit=args.limit,
            allow_partial=args.allow_partial,
        )
    except ValueError as exc:
        print(f"Submission build error: {exc}", file=sys.stderr)
        return 2

    validation = validate_submission_rows(result.rows, expected_count=len(result.rows) if args.allow_partial else 100)
    print(format_submission_validation_report(validation))
    if not validation.is_valid:
        print("Internal validation failed; not writing final output files.", file=sys.stderr)
        return 1

    write_submission_csv(result.rows, args.out)
    print(f"Wrote submission CSV to {args.out}")
    if args.xlsx:
        write_submission_xlsx(result.rows, args.xlsx)
        print(f"Wrote submission XLSX to {args.xlsx}")
    if args.debug_csv:
        write_debug_csv(result.debug_rows, args.debug_csv)
        print(f"Wrote debug submission CSV to {args.debug_csv}")

    external_output = ""
    if not args.skip_external_validator and not args.allow_partial:
        external_output = _run_external_validator(args.out)
        if external_output:
            print(external_output.rstrip())

    warnings = list(result.warnings)
    if external_output:
        warnings.append("External validator output captured in console.")

    report_result = result
    report_result.warnings = warnings
    if args.report_out:
        runtime_report = build_runtime_report(report_result, args.candidates, args.out, args.xlsx, validation)
        write_runtime_report(runtime_report, args.report_out)
        print(f"Wrote submission run report to {args.report_out}")

    print(
        "Submission generation complete: "
        f"submitted={result.submitted_count}, total_seen={result.total_seen}, "
        f"ranking_quality={result.ranking_quality_summary}, reasoning_quality={result.reasoning_quality_summary}"
    )
    return 0


def main() -> int:
    return run_submission_cli(build_parser().parse_args())


def _run_external_validator(csv_path: str | Path) -> str:
    validator = _find_external_validator()
    if validator is None:
        return "External validate_submission.py not found; skipped."
    command = [sys.executable, str(validator), str(csv_path)]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        return f"External validator could not run: {exc}"
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        return "External validator reported issues:\n" + output
    return "External validator passed:\n" + output


def _find_external_validator() -> Path | None:
    candidates = [
        Path("validate_submission.py"),
        Path("/Users/jaypandey/Downloads/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py"),
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


if __name__ == "__main__":
    raise SystemExit(main())
