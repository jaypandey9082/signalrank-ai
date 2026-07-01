from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.final_gate import GateIssue, check_portal_packet, escape_md
from src.utils import ensure_parent_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check SignalRank AI portal upload packet readiness.")
    parser.add_argument("--github-url", required=True)
    parser.add_argument("--sandbox-url", required=True)
    parser.add_argument("--deck", required=True)
    parser.add_argument("--xlsx", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--report-out", default="outputs/final_portal_packet_report.md")
    return parser


def portal_packet_markdown(
    *,
    github_url: str,
    sandbox_url: str,
    deck: str,
    xlsx: str,
    csv_path: str,
    issues: list[GateIssue],
) -> str:
    blockers = [issue for issue in issues if issue.severity == "blocker"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    status = "BLOCKED" if blockers else "WARN" if warnings else "PASS"
    lines = [
        "# Portal Packet Report",
        "",
        f"- Status: {status}",
        f"- GitHub URL: `{github_url}`",
        f"- Sandbox URL: `{sandbox_url}`",
        f"- Deck: `{deck}`",
        f"- XLSX: `{xlsx}`",
        f"- CSV: `{csv_path}`",
        "",
        "## Upload Checklist",
        "",
        f"- GitHub repository URL: {'ready' if not any(i.code == 'github_url' for i in issues) else 'blocked'}",
        f"- Sandbox/demo URL: {'ready' if not any(i.code == 'sandbox_url' for i in issues) else 'blocked'}",
        f"- Deck PDF: {'ready' if not any(i.code.startswith('deck') for i in issues) else 'blocked'}",
        f"- XLSX output: {'ready' if not any(i.code.startswith('xlsx') for i in issues) else 'blocked'}",
        f"- CSV output: {'ready' if not any(i.code.startswith('csv') for i in issues) else 'blocked'}",
    ]
    if issues:
        lines.extend(["", "## Issues", "", "| Severity | Code | Message |", "|---|---|---|"])
        lines.extend(f"| {issue.severity} | `{issue.code}` | {escape_md(issue.message)} |" for issue in issues)
    else:
        lines.extend(["", "No portal packet blockers found."])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = build_parser().parse_args()
    issues = check_portal_packet(
        github_url=args.github_url,
        sandbox_url=args.sandbox_url,
        deck_path=args.deck,
        xlsx_path=args.xlsx,
        csv_path=args.csv,
    )
    markdown = portal_packet_markdown(
        github_url=args.github_url,
        sandbox_url=args.sandbox_url,
        deck=args.deck,
        xlsx=args.xlsx,
        csv_path=args.csv,
        issues=issues,
    )
    ensure_parent_dir(args.report_out)
    Path(args.report_out).write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"Wrote portal packet report to {args.report_out}")
    return 0 if not any(issue.severity == "blocker" for issue in issues) else 1


if __name__ == "__main__":
    raise SystemExit(main())
