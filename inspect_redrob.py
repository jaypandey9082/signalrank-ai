from __future__ import annotations

import argparse
from pathlib import Path

from src.load_data import CandidateDataError
from src.redrob_inspector import (
    format_redrob_console_report,
    format_redrob_markdown_report,
    inspect_redrob_scores,
    redrob_rows_to_csv,
)
from src.scoring_config import DEFAULT_AS_OF_DATE
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect Redrob behavior and hireability signals.")
    parser.add_argument("--candidates", required=True, help="Path to candidate JSON/JSONL/JSONL.GZ file.")
    parser.add_argument("--limit", type=int, help="Maximum number of records to inspect.")
    parser.add_argument("--top", type=int, default=20, help="Number of high/low examples to show.")
    parser.add_argument("--as-of-date", default=DEFAULT_AS_OF_DATE, help="Reference date for recency scoring.")
    parser.add_argument("--report-out", help="Optional path for a markdown Redrob behavior report.")
    parser.add_argument("--debug-csv", help="Optional path for debug Redrob rows CSV.")
    parser.add_argument("--include-static-preview", action="store_true", help="Show static-fit x behavior preview rows.")
    parser.add_argument("--allow-full", action="store_true", help="Allow an unbounded candidates.jsonl inspection.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    candidate_path = Path(args.candidates)

    if candidate_path.name in {"candidates.jsonl", "candidates.jsonl.gz"} and args.limit is None:
        if not args.allow_full:
            parser.exit(
                2,
                "Refusing to inspect full candidates file without --limit. "
                "Use --limit for Section 6 smoke tests or pass --allow-full explicitly.\n",
            )
        print("This is Redrob behavior inspection, not the final ranking run.")

    try:
        report = inspect_redrob_scores(
            args.candidates,
            limit=args.limit,
            top_n=args.top,
            as_of_date=args.as_of_date,
            include_static_preview=args.include_static_preview,
        )
    except CandidateDataError as exc:
        parser.exit(1, f"Data loading error: {exc}\n")

    print(format_redrob_console_report(report))

    if args.report_out:
        report_path = Path(args.report_out)
        ensure_parent_dir(report_path)
        report_path.write_text(format_redrob_markdown_report(report), encoding="utf-8")
        print(f"\nWrote Redrob behavior report to {report_path}")

    if args.debug_csv:
        debug_path = Path(args.debug_csv)
        redrob_rows_to_csv(report.high_hireability_examples, debug_path)
        print(f"Wrote debug Redrob rows to {debug_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
