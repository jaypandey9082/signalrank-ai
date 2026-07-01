from __future__ import annotations

import argparse
import cProfile
import pstats
from pathlib import Path

from src.submission import build_submission_rows
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Profile SignalRank AI submission generation.")
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--top-k", type=int, default=100)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--profile-out", default="outputs/submission_profile.txt")
    parser.add_argument("--sort", default="cumtime")
    parser.add_argument("--lines", type=int, default=40)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    profiler = cProfile.Profile()
    profiler.enable()
    build_submission_rows(args.candidates, top_k=args.top_k, limit=args.limit, allow_partial=args.allow_partial)
    profiler.disable()

    ensure_parent_dir(args.profile_out)
    with Path(args.profile_out).open("w", encoding="utf-8") as handle:
        stats = pstats.Stats(profiler, stream=handle)
        stats.strip_dirs().sort_stats(args.sort).print_stats(args.lines)
    print(f"Wrote profile to {args.profile_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
