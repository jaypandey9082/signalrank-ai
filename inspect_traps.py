from __future__ import annotations

import argparse
from pathlib import Path

from src.load_data import CandidateDataError
from src.trap_inspector import (
    format_trap_console_report,
    format_trap_markdown_report,
    inspect_traps,
    trap_rows_to_csv,
)
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect trap and honeypot-like penalty signals.")
    parser.add_argument("--candidates", required=True, help="Path to candidate JSON/JSONL/JSONL.GZ file.")
    parser.add_argument("--limit", type=int, help="Maximum number of records to inspect.")
    parser.add_argument("--top", type=int, default=25, help="Number of high/clean examples to show.")
    parser.add_argument("--report-out", help="Optional path for a markdown trap inspection report.")
    parser.add_argument("--debug-csv", help="Optional path for debug trap rows CSV.")
    parser.add_argument("--include-preview", action="store_true", help="Show static x behavior x trap preview rows.")
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
                "Use --limit for Section 7 smoke tests or pass --allow-full explicitly.\n",
            )
        print("This is trap inspection, not the final ranking run.")

    try:
        report = inspect_traps(
            args.candidates,
            limit=args.limit,
            top_n=args.top,
            include_preview=args.include_preview,
        )
    except CandidateDataError as exc:
        parser.exit(1, f"Data loading error: {exc}\n")

    print(format_trap_console_report(report))

    if args.report_out:
        report_path = Path(args.report_out)
        ensure_parent_dir(report_path)
        report_path.write_text(format_trap_markdown_report(report), encoding="utf-8")
        print(f"\nWrote trap inspection report to {report_path}")

    if args.debug_csv:
        debug_path = Path(args.debug_csv)
        trap_rows_to_csv(report.debug_rows, debug_path)
        print(f"Wrote debug trap rows to {debug_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
