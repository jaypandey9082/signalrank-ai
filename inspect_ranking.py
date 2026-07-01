from __future__ import annotations

import argparse
from pathlib import Path

from src.load_data import CandidateDataError
from src.ranking import (
    format_ranking_console_report,
    format_ranking_markdown_report,
    rank_candidates_preview,
    write_ranking_preview_csv,
)
from src.ranking_quality import evaluate_ranking_quality, format_quality_markdown
from src.scoring_config import RANKING_DEFAULT_TOP_K
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect combined SignalRank ranking previews.")
    parser.add_argument("--candidates", required=True, help="Path to candidate JSON/JSONL/JSONL.GZ file.")
    parser.add_argument("--limit", type=int, help="Maximum number of records to rank.")
    parser.add_argument("--top", type=int, default=RANKING_DEFAULT_TOP_K, help="Number of preview rows to keep.")
    parser.add_argument("--report-out", help="Optional path for a markdown ranking preview report.")
    parser.add_argument("--debug-csv", help="Optional path for debug ranking preview CSV.")
    parser.add_argument("--quality-out", help="Optional path for a markdown ranking quality report.")
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
                "Refusing to rank full candidates file without --limit. "
                "Use --limit for Section 8 previews or pass --allow-full explicitly.\n",
            )
        print("This is a ranking preview, not the final challenge submission.")

    try:
        result = rank_candidates_preview(
            args.candidates,
            top_k=args.top,
            limit=args.limit,
        )
    except CandidateDataError as exc:
        parser.exit(1, f"Data loading error: {exc}\n")

    print(format_ranking_console_report(result))
    quality = evaluate_ranking_quality(result.rows)
    if quality.warnings:
        print("\nRanking quality warnings:")
        for warning in quality.warnings:
            print(f"- {warning}")
    else:
        print("\nRanking quality checks passed.")

    if args.report_out:
        report_path = Path(args.report_out)
        ensure_parent_dir(report_path)
        report_path.write_text(format_ranking_markdown_report(result), encoding="utf-8")
        print(f"\nWrote ranking preview report to {report_path}")

    if args.quality_out:
        quality_path = Path(args.quality_out)
        ensure_parent_dir(quality_path)
        quality_path.write_text(format_quality_markdown(quality), encoding="utf-8")
        print(f"Wrote ranking quality report to {quality_path}")

    if args.debug_csv:
        debug_path = Path(args.debug_csv)
        write_ranking_preview_csv(result.rows, debug_path)
        print(f"Wrote ranking preview debug CSV to {debug_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
