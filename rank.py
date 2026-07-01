from __future__ import annotations

import argparse

from generate_submission import run_submission_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Official fast SignalRank AI CSV ranking command.")
    parser.add_argument("--candidates", required=True, help="Path to candidate JSON/JSONL/JSONL.GZ file.")
    parser.add_argument("--out", required=True, help="Path for final submission CSV.")
    parser.add_argument("--xlsx", help="Optional path for XLSX export.")
    parser.add_argument("--report-out", help="Optional path for markdown run report.")
    parser.add_argument("--debug-csv", help="Optional path for debug submission CSV.")
    parser.add_argument("--top-k", type=int, default=100, help="Submission size. Must be 100 unless --allow-partial.")
    parser.add_argument("--limit", type=int, help="Limit candidate rows. Only allowed with --allow-partial.")
    parser.add_argument("--allow-partial", action="store_true", help="Allow partial/sample submission generation for tests.")
    parser.add_argument("--run-external-validator", action="store_true", help="Run bundled validate_submission.py after writing CSV.")
    parser.add_argument("--skip-external-validator", action="store_true", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.skip_external_validator = not args.run_external_validator
    return run_submission_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
