from __future__ import annotations

import argparse
from pathlib import Path

from src.jd_signals import (
    match_terms,
    signal_map_to_markdown,
    summarize_signal_map,
)
from src.scoring_config import scoring_config_to_markdown
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the SignalRank AI JD signal map.")
    parser.add_argument("--markdown-out", help="Optional path for writing the JD signal map markdown.")
    parser.add_argument("--text", help="Optional text to match against the signal map.")
    parser.add_argument("--show-weights", action="store_true", help="Also print draft scoring weights.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.text:
        matches = match_terms(args.text)
        print("Matched signal groups")
        print("=====================")
        if not matches:
            print("No terms matched.")
        else:
            for group_name, terms in matches.items():
                print(f"- {group_name}: {', '.join(terms)}")
    else:
        print(summarize_signal_map())

    if args.markdown_out:
        output_path = Path(args.markdown_out)
        ensure_parent_dir(output_path)
        output_path.write_text(signal_map_to_markdown(), encoding="utf-8")
        print(f"\nWrote JD signal map to {output_path}")

    if args.show_weights:
        print()
        print(scoring_config_to_markdown())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
