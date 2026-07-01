from __future__ import annotations

import argparse
from pathlib import Path

from src.load_data import CandidateDataError
from src.reasoning_inspector import (
    build_reasoning_preview,
    format_reasoning_console_report,
    format_reasoning_markdown_report,
    write_reasoning_preview_csv,
)
from src.reasoning_quality import format_reasoning_quality_markdown
from src.scoring_config import RANKING_DEFAULT_TOP_K
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect evidence-based reasoning previews.")
    parser.add_argument("--candidates", required=True, help="Path to candidate JSON/JSONL/JSONL.GZ file.")
    parser.add_argument("--limit", type=int, help="Maximum number of records to rank before reasoning.")
    parser.add_argument("--top", type=int, default=RANKING_DEFAULT_TOP_K, help="Number of ranked rows to reason over.")
    parser.add_argument("--report-out", help="Optional path for a markdown reasoning preview report.")
    parser.add_argument("--quality-out", help="Optional path for a markdown reasoning quality report.")
    parser.add_argument("--debug-csv", help="Optional path for debug reasoning preview CSV.")
    parser.add_argument("--allow-full", action="store_true", help="Allow an unbounded candidates.jsonl preview.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    candidate_path = Path(args.candidates)

    if candidate_path.name in {"candidates.jsonl", "candidates.jsonl.gz"} and args.limit is None:
        if not args.allow_full:
            parser.exit(
                2,
                "Refusing to build reasoning for full candidates file without --limit. "
                "Use --limit for Section 9 previews or pass --allow-full explicitly.\n",
            )
        print("This is a reasoning preview, not the final challenge submission.")

    try:
        report = build_reasoning_preview(
            args.candidates,
            top_k=args.top,
            limit=args.limit,
        )
    except CandidateDataError as exc:
        parser.exit(1, f"Data loading error: {exc}\n")

    print(format_reasoning_console_report(report))

    if args.report_out:
        report_path = Path(args.report_out)
        ensure_parent_dir(report_path)
        report_path.write_text(format_reasoning_markdown_report(report), encoding="utf-8")
        print(f"\nWrote reasoning preview report to {report_path}")

    if args.quality_out:
        quality_path = Path(args.quality_out)
        ensure_parent_dir(quality_path)
        quality_path.write_text(format_reasoning_quality_markdown(report.quality_report), encoding="utf-8")
        print(f"Wrote reasoning quality report to {quality_path}")

    if args.debug_csv:
        debug_path = Path(args.debug_csv)
        write_reasoning_preview_csv(report.preview_rows, debug_path)
        print(f"Wrote reasoning preview debug CSV to {debug_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
