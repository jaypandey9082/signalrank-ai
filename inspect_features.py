from __future__ import annotations

import argparse
from pathlib import Path

from src.feature_inspector import (
    feature_rows_to_csv,
    format_feature_console_report,
    format_feature_markdown_report,
    inspect_features,
)
from src.load_data import CandidateDataError
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect extracted SignalRank AI features.")
    parser.add_argument("--candidates", required=True, help="Path to candidate JSON/JSONL/JSONL.GZ file.")
    parser.add_argument("--limit", type=int, help="Maximum number of records to inspect.")
    parser.add_argument("--show", type=int, default=10, help="Number of sample rows to include.")
    parser.add_argument("--report-out", help="Optional path for a markdown feature report.")
    parser.add_argument("--debug-csv", help="Optional path for debug feature rows CSV.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    candidate_path = Path(args.candidates)
    if candidate_path.name in {"candidates.jsonl", "candidates.jsonl.gz"} and args.limit is None:
        print("Tip: use --limit for full dataset inspection in Section 4.")

    try:
        report = inspect_features(args.candidates, limit=args.limit, sample_size=args.show)
    except CandidateDataError as exc:
        parser.exit(1, f"Data loading error: {exc}\n")

    print(format_feature_console_report(report))

    if args.report_out:
        report_path = Path(args.report_out)
        ensure_parent_dir(report_path)
        report_path.write_text(format_feature_markdown_report(report), encoding="utf-8")
        print(f"\nWrote feature report to {report_path}")

    if args.debug_csv:
        debug_path = Path(args.debug_csv)
        feature_rows_to_csv(report.sample_rows, debug_path)
        print(f"Wrote debug feature rows to {debug_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
