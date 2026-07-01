from __future__ import annotations

import argparse
from pathlib import Path

from src.config import DEFAULT_INSPECTION_SAMPLE_SIZE
from src.inspect import format_console_report, format_markdown_report, inspect_candidates
from src.load_data import CandidateDataError
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect SignalRank AI candidate data.")
    parser.add_argument("--candidates", required=True, help="Path to candidate JSON/JSONL/JSONL.GZ file.")
    parser.add_argument("--limit", type=int, help="Maximum number of records to inspect.")
    parser.add_argument(
        "--show-samples",
        type=int,
        default=DEFAULT_INSPECTION_SAMPLE_SIZE,
        help="Number of sample candidate briefs to show.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit with code 2 if invalid candidates are found.")
    parser.add_argument("--report-out", help="Optional path for a markdown inspection report.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        report = inspect_candidates(
            args.candidates,
            limit=args.limit,
            sample_size=args.show_samples,
            strict=args.strict,
        )
    except CandidateDataError as exc:
        parser.exit(1, f"Data loading error: {exc}\n")

    print(format_console_report(report))

    if args.report_out:
        report_path = Path(args.report_out)
        ensure_parent_dir(report_path)
        report_path.write_text(format_markdown_report(report), encoding="utf-8")
        print(f"\nWrote markdown report to {report_path}")

    if args.strict and report.invalid_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
