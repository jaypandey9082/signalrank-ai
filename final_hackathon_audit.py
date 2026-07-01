from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.check_portal_packet import portal_packet_markdown
from scripts.final_gate import (
    GateIssue,
    check_portal_packet,
    check_url,
    environment_snapshot,
    escape_md,
    run_final_gate,
)
from src.export import read_submission_csv
from src.reasoning_quality import has_jd_connection, has_specific_fact, is_too_generic
from src.utils import ensure_parent_dir


ROOT = Path(__file__).resolve().parent
REQUIRED_PREFLIGHT = (
    "rank.py",
    "generate_submission.py",
    "benchmark_submission.py",
    "audit_submission.py",
    "sandbox/app.py",
    "src/submission.py",
    "src/submission_validator.py",
    "src/ranking.py",
    "src/combined_scoring.py",
    "src/reasoning.py",
    "src/reasoning_quality.py",
    "src/repo_audit.py",
    "src/reproducibility.py",
    "src/export.py",
    "FINAL_SUBMISSION_CHECKLIST.md",
    "SUBMISSION_PACKET.md",
    "DEPLOYMENT.md",
    "DEMO_SCRIPT.md",
    "submission_metadata.yaml",
    "README.md",
    "deck/approach_deck.md",
    "deck/approach_deck.html",
)
DOC_CHECKS = (
    "deck/approach_deck.md",
    "deck/approach_deck.html",
    "FINAL_SUBMISSION_CHECKLIST.md",
    "SUBMISSION_PACKET.md",
    "DEPLOYMENT.md",
    "DEMO_SCRIPT.md",
    "docs/final_methodology.md",
    "docs/architecture_overview.md",
    "docs/judging_notes.md",
    "sandbox/README.md",
    "docs/sandbox_demo.md",
    "docs/hosted_demo_guide.md",
)
TARGET_TERMS = (
    "ranking",
    "retrieval",
    "search",
    "recommendation",
    "recommender",
    "evaluation",
    "production",
    "ml",
    "ai",
)
WRONG_ROLE_TERMS = ("marketing", "sales", "recruiter", "hr ", "operations", "finance")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run final SignalRank AI hackathon readiness audit.")
    parser.add_argument("--candidates")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--xlsx")
    parser.add_argument("--deck")
    parser.add_argument("--sandbox-url")
    parser.add_argument("--github-url")
    parser.add_argument("--report-out", default="outputs/final_hackathon_audit.md")
    parser.add_argument("--skip-runtime-benchmark", action="store_true")
    parser.add_argument("--skip-streamlit-smoke", action="store_true")
    parser.add_argument("--skip-external-validator", action="store_true")
    parser.add_argument("--allow-placeholder-metadata", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    missing_preflight = [path for path in REQUIRED_PREFLIGHT if not (ROOT / path).exists()]
    optional_missing = []
    if not (ROOT / "validate_submission.py").exists():
        optional_missing.append("validate_submission.py missing from repo root; external bundle path may still be used.")
    if args.deck and not Path(args.deck).is_absolute() and not (ROOT / args.deck).exists():
        optional_missing.append(f"Deck path missing: {args.deck}")

    gate = run_final_gate(
        candidates_path=args.candidates,
        csv_path=args.csv,
        xlsx_path=args.xlsx,
        deck_path=args.deck,
        root=ROOT,
        skip_runtime_benchmark=args.skip_runtime_benchmark,
        skip_external_validator=args.skip_external_validator,
        allow_placeholder_metadata=args.allow_placeholder_metadata,
    )

    audit_issues = list(gate.issues)
    for missing in missing_preflight:
        audit_issues.append(GateIssue("blocker", "preflight_missing", f"Required preflight file missing: {missing}"))
    for note in optional_missing:
        audit_issues.append(GateIssue("warning", "preflight_optional_missing", note))

    github_url = args.github_url or "TODO"
    sandbox_url = args.sandbox_url or "TODO"
    audit_issues.extend(check_url(github_url, "github_url", "GitHub repo URL"))
    audit_issues.extend(check_url(sandbox_url, "sandbox_url", "Sandbox/demo URL"))

    quality = build_quality_review(args.csv)
    quality_report_out = ROOT / "outputs/final_submission_quality_report.md"
    ensure_parent_dir(quality_report_out)
    quality_report_out.write_text(build_quality_markdown(quality), encoding="utf-8")
    audit_issues.extend(quality["issues"])
    sandbox = run_sandbox_smoke(skip=args.skip_streamlit_smoke)
    audit_issues.extend(sandbox["issues"])
    docs = check_docs(args.deck)
    audit_issues.extend(docs["issues"])

    portal_issues = check_portal_packet(
        github_url=github_url,
        sandbox_url=sandbox_url,
        deck_path=args.deck or "deck/SignalRank_AI_Approach_Deck.pdf",
        xlsx_path=args.xlsx or "outputs/submission.xlsx",
        csv_path=args.csv,
        root=ROOT,
    )

    blockers = [issue for issue in audit_issues if issue.severity == "blocker"]
    warnings = [issue for issue in audit_issues if issue.severity == "warning"]
    status = "BLOCKED" if blockers else "WARN" if warnings else "PASS"
    upload_ready = status == "PASS" and not any(issue.severity == "blocker" for issue in portal_issues)
    confidence = "High" if upload_ready else "Medium" if gate.validation and gate.validation.is_valid else "Low"

    markdown = build_audit_markdown(
        args=args,
        status=status,
        upload_ready=upload_ready,
        confidence=confidence,
        gate=gate,
        audit_issues=audit_issues,
        portal_issues=portal_issues,
        missing_preflight=missing_preflight,
        optional_missing=optional_missing,
        quality=quality,
        sandbox=sandbox,
        docs=docs,
        github_url=github_url,
        sandbox_url=sandbox_url,
    )
    ensure_parent_dir(args.report_out)
    Path(args.report_out).write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"Wrote final hackathon audit to {args.report_out}")
    return 0 if status != "BLOCKED" else 1


def build_quality_review(csv_path: str | Path) -> dict[str, Any]:
    path = Path(csv_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return {"issues": [GateIssue("blocker", "quality_csv_missing", "CSV missing; cannot review ranking/reasoning quality.")], "summary": {}, "sample": []}
    rows = read_submission_csv(path)
    top10 = rows[:10]
    top100 = rows[:100]
    top10_target = sum(_has_any(row.get("reasoning", ""), TARGET_TERMS) for row in top10)
    top10_wrong = sum(_has_any(row.get("reasoning", ""), WRONG_ROLE_TERMS) for row in top10)
    top100_target = sum(_has_any(row.get("reasoning", ""), TARGET_TERMS) for row in top100)
    reasoning_texts = [str(row.get("reasoning", "")) for row in top100]
    empty_count = sum(1 for text in reasoning_texts if not text.strip())
    generic_count = sum(1 for text in reasoning_texts if is_too_generic(text))
    too_long_count = sum(1 for text in reasoning_texts if len(text) > 500)
    missing_jd_count = sum(1 for text in reasoning_texts if not has_jd_connection(text))
    missing_fact_count = sum(1 for text in reasoning_texts if not has_specific_fact(text))
    repeated_count = len(reasoning_texts) - len(set(reasoning_texts))
    issues: list[GateIssue] = []
    if top10_target < 6:
        issues.append(GateIssue("warning", "quality_top10_target_terms_low", f"Only {top10_target}/10 top reasonings mention target evidence terms."))
    if top10_wrong:
        issues.append(GateIssue("warning", "quality_top10_wrong_role_terms", f"{top10_wrong}/10 top reasonings mention wrong-role terms."))
    if empty_count:
        issues.append(GateIssue("blocker", "reasoning_empty", f"{empty_count} top-100 reasonings are empty."))
    if too_long_count:
        issues.append(GateIssue("blocker", "reasoning_too_long", f"{too_long_count} top-100 reasonings exceed 500 chars."))
    if generic_count or missing_jd_count or missing_fact_count or repeated_count:
        issues.append(
            GateIssue(
                "warning",
                "reasoning_quality_proxy",
                "Reasoning proxy checks need manual review.",
                evidence=f"generic={generic_count}, missing_jd={missing_jd_count}, missing_fact={missing_fact_count}, repeated={repeated_count}",
            )
        )
    sample = deterministic_reasoning_sample(rows)
    return {
        "issues": issues,
        "summary": {
            "top10_target_evidence_count": top10_target,
            "top10_wrong_role_count": top10_wrong,
            "top100_target_evidence_count": top100_target,
            "reasoning_errors": empty_count + too_long_count,
            "reasoning_warnings": generic_count + missing_jd_count + missing_fact_count + repeated_count,
        },
        "sample": sample,
    }


def deterministic_reasoning_sample(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    indices = sorted(set([0, 1, 2, 9, 19, 29, 49, 69, 89, min(99, len(rows) - 1)]))
    return [rows[index] for index in indices if index < len(rows)]


def build_quality_markdown(quality: dict[str, Any]) -> str:
    summary = quality.get("summary", {})
    lines = [
        "# Final Submission Quality Report",
        "",
        f"- Top 10 target-evidence reasonings: {summary.get('top10_target_evidence_count', 'n/a')}",
        f"- Top 10 wrong-role mentions: {summary.get('top10_wrong_role_count', 'n/a')}",
        f"- Top 100 target-evidence reasonings: {summary.get('top100_target_evidence_count', 'n/a')}",
        f"- Reasoning quality errors: {summary.get('reasoning_errors', 'n/a')}",
        f"- Reasoning quality warnings: {summary.get('reasoning_warnings', 'n/a')}",
    ]
    if quality.get("issues"):
        lines.extend(["", "## Issues"])
        lines.extend(f"- `{issue.severity}` `{issue.code}`: {issue.message}" for issue in quality["issues"])
    lines.extend(["", "## Manual Reasoning Sample", "", "| Rank | Candidate | Score | Reasoning |", "|---:|---|---:|---|"])
    for row in quality.get("sample", []):
        lines.append(f"| {row.get('rank', '')} | {row.get('candidate_id', '')} | {row.get('score', '')} | {escape_md(row.get('reasoning', ''))} |")
    return "\n".join(lines) + "\n"


def run_sandbox_smoke(*, skip: bool) -> dict[str, Any]:
    if skip:
        return {"issues": [GateIssue("warning", "sandbox_smoke_skipped", "Sandbox smoke was skipped by flag.")], "output": "skipped"}
    issues: list[GateIssue] = []
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_sandbox_helpers.py", "tests/test_ui_components.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        issues.append(GateIssue("blocker", "sandbox_tests_failed", "Sandbox helper/UI tests failed.", output[-1000:]))
    return {"issues": issues, "output": output.strip() or "passed"}


def check_docs(deck_path: str | Path | None) -> dict[str, Any]:
    issues: list[GateIssue] = []
    existing = []
    missing = []
    for rel_path in DOC_CHECKS:
        if (ROOT / rel_path).exists():
            existing.append(rel_path)
        else:
            missing.append(rel_path)
            issues.append(GateIssue("warning", "doc_missing", f"Documentation file missing: {rel_path}"))
    if deck_path:
        deck = Path(deck_path)
        if not deck.is_absolute():
            deck = ROOT / deck
        if not deck.exists():
            issues.append(GateIssue("blocker", "deck_pdf_missing", f"Deck PDF missing: {deck}"))
        elif deck.stat().st_size > 5 * 1024 * 1024:
            issues.append(GateIssue("blocker", "deck_pdf_too_large", f"Deck PDF exceeds 5 MB: {deck.stat().st_size} bytes."))
    return {"issues": issues, "existing": existing, "missing": missing}


def build_audit_markdown(
    *,
    args: argparse.Namespace,
    status: str,
    upload_ready: bool,
    confidence: str,
    gate,
    audit_issues: list[GateIssue],
    portal_issues: list[GateIssue],
    missing_preflight: list[str],
    optional_missing: list[str],
    quality: dict[str, Any],
    sandbox: dict[str, Any],
    docs: dict[str, Any],
    github_url: str,
    sandbox_url: str,
) -> str:
    env = environment_snapshot(ROOT)
    blockers = [issue for issue in audit_issues if issue.severity == "blocker"]
    warnings = [issue for issue in audit_issues if issue.severity == "warning"]
    checklist = requirement_checklist(gate, audit_issues, portal_issues)
    lines = [
        "# Final Hackathon Audit — SignalRank AI",
        "",
        "## Executive Summary",
        "",
        f"- Overall status: {status}",
        f"- Upload readiness: {'yes' if upload_ready else 'no'}",
        f"- Winning-quality confidence: {confidence}",
        f"- Main blockers: {len(blockers)}",
        f"- Main warnings: {len(warnings)}",
    ]
    if blockers:
        lines.extend(f"- BLOCKER `{issue.code}`: {issue.message}" for issue in blockers[:10])
    if warnings:
        lines.extend(f"- WARN `{issue.code}`: {issue.message}" for issue in warnings[:10])

    lines.extend(
        [
            "",
            "## Environment",
            "",
            f"- Python: {env['python']}",
            f"- Platform: {env['platform']}",
            f"- Git branch: {env['git_branch']}",
            f"- GPU required: {env['gpu_required']}",
            f"- Network required during ranking: {env['network_required_during_ranking']}",
            "",
            "## Requirement Checklist",
            "",
            "| Requirement | Status | Evidence |",
            "|---|---|---|",
        ]
    )
    lines.extend(f"| {name} | {status_text} | {escape_md(evidence)} |" for name, status_text, evidence in checklist)

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- CSV path: `{args.csv}`",
            f"- XLSX path: `{args.xlsx or 'not provided'}`",
            f"- Deck path: `{args.deck or 'not provided'}`",
            f"- Sandbox URL: `{sandbox_url}`",
            f"- GitHub URL: `{github_url}`",
            "",
            "## Runtime",
            "",
        ]
    )
    if gate.runtime:
        lines.extend(
            [
                f"- Latest measured official command runtime: {gate.runtime.elapsed_seconds}",
                f"- Runtime status: {gate.runtime.status}",
                f"- Runtime message: {gate.runtime.message}",
            ]
        )
    else:
        lines.append("- Runtime benchmark: not run")
    if gate.determinism:
        lines.extend(
            [
                "",
                "## Determinism",
                "",
                f"- Status: {gate.determinism.status}",
                f"- Same hash: {gate.determinism.same_hash}",
                f"- Hash A: {gate.determinism.hash_a}",
                f"- Hash B: {gate.determinism.hash_b}",
            ]
        )

    lines.extend(
        [
            "",
            "## Quality Review",
            "",
            f"- Top 10 target-evidence reasonings: {quality['summary'].get('top10_target_evidence_count', 'n/a')}",
            f"- Top 10 wrong-role mentions: {quality['summary'].get('top10_wrong_role_count', 'n/a')}",
            f"- Top 100 target-evidence reasonings: {quality['summary'].get('top100_target_evidence_count', 'n/a')}",
            f"- Reasoning quality errors: {quality['summary'].get('reasoning_errors', 'n/a')}",
            f"- Reasoning quality warnings: {quality['summary'].get('reasoning_warnings', 'n/a')}",
            "",
            "### Manual Reasoning Sample",
            "",
            "| Rank | Candidate | Score | Reasoning |",
            "|---:|---|---:|---|",
        ]
    )
    for row in quality.get("sample", []):
        lines.append(f"| {row.get('rank', '')} | {row.get('candidate_id', '')} | {row.get('score', '')} | {escape_md(row.get('reasoning', ''))} |")

    lines.extend(
        [
            "",
            "## Repo Audit",
            "",
            f"- Repo issue count from gate: {gate.repo_issue_count}",
            f"- Missing required preflight files: {', '.join(missing_preflight) if missing_preflight else 'none'}",
            f"- Optional/preflight warnings: {', '.join(optional_missing) if optional_missing else 'none'}",
            "",
            "## Sandbox",
            "",
            "```text",
            str(sandbox.get("output", ""))[-2000:],
            "```",
            "",
            "## Deck And Docs",
            "",
            f"- Existing docs checked: {len(docs.get('existing', []))}",
            f"- Missing docs checked: {', '.join(docs.get('missing', [])) if docs.get('missing') else 'none'}",
            "- Quality report: `outputs/final_submission_quality_report.md`",
            "",
            "## Portal Upload Checklist",
            "",
        ]
    )
    lines.append(
        portal_packet_markdown(
            github_url=github_url,
            sandbox_url=sandbox_url,
            deck=args.deck or "deck/SignalRank_AI_Approach_Deck.pdf",
            xlsx=args.xlsx or "outputs/submission.xlsx",
            csv_path=args.csv,
            issues=portal_issues,
        ).strip()
    )
    if gate.external_validator_output:
        lines.extend(["", "## External Validator", "", "```text", gate.external_validator_output.strip(), "```"])
    if audit_issues:
        lines.extend(["", "## All Audit Issues", "", "| Severity | Code | Message | Evidence |", "|---|---|---|---|"])
        for issue in audit_issues:
            lines.append(f"| {issue.severity} | `{issue.code}` | {escape_md(issue.message)} | {escape_md(issue.evidence)} |")
    lines.extend(
        [
            "",
            "## Final Recommendation",
            "",
            "Proceed with upload." if upload_ready else "Fix blockers first.",
            "",
            "Specific next actions:",
        ]
    )
    if blockers:
        lines.extend(f"- Fix `{issue.code}`: {issue.message}" for issue in blockers[:12])
    else:
        lines.append("- No hard blockers detected by this audit.")
    return "\n".join(lines) + "\n"


def requirement_checklist(gate, audit_issues: list[GateIssue], portal_issues: list[GateIssue]) -> list[tuple[str, str, str]]:
    issue_codes = {issue.code for issue in audit_issues}
    portal_codes = {issue.code for issue in portal_issues}
    return [
        ("Exact CSV columns", _status(gate.validation and gate.validation.is_valid), "Internal validator checks required columns."),
        ("100 rows", _status(gate.validation and gate.validation.row_count == 100), f"Rows={gate.validation.row_count if gate.validation else 'n/a'}"),
        ("Unique ranks", _status(gate.validation and not _has_validation_issue(gate.validation, "duplicate_rank")), "Internal validation."),
        ("Unique candidate IDs", _status(gate.validation and not _has_validation_issue(gate.validation, "duplicate_candidate_id")), "Internal validation."),
        ("Score monotonicity", _status(gate.validation and not _has_validation_issue(gate.validation, "score_increasing")), "Internal validation."),
        ("External validator", "WARN" if "external_validator_missing" in issue_codes or "external_validator_skipped" in issue_codes else _status(bool(gate.external_validator_output and gate.external_validator_output.startswith("External validator passed"))), "validate_submission.py external/bundled check."),
        ("Runtime under 5 min", _runtime_status(gate.runtime), gate.runtime.message if gate.runtime else "Not run."),
        ("CPU-only/no-network", _status("metadata_network_flag" not in issue_codes and "metadata_gpu_flag" not in issue_codes), "Metadata and repo audit."),
        ("Deterministic repeat", _status(gate.determinism and gate.determinism.same_hash), gate.determinism.message if gate.determinism else "Not run."),
        ("Repo hygiene", _status(not any(issue.code.startswith("repo_") and issue.severity == "blocker" for issue in audit_issues)), "Repo audit checks."),
        ("Metadata", _status("metadata_placeholders" not in issue_codes and "metadata_missing" not in issue_codes), "submission_metadata.yaml."),
        ("Deck", _status("deck_missing" not in issue_codes and "deck_pdf_missing" not in issue_codes and "deck" not in portal_codes), "Deck PDF check."),
        ("Sandbox", _status("sandbox_tests_failed" not in issue_codes), "Sandbox helper/UI tests."),
        ("XLSX portal file", _status(gate.xlsx_parity and gate.xlsx_parity.get("passed")), "CSV/XLSX parity."),
    ]


def _status(value: Any) -> str:
    return "PASS" if bool(value) else "BLOCKED"


def _runtime_status(runtime) -> str:
    if runtime is None:
        return "WARN"
    return "PASS" if runtime.status == "PASS" else runtime.status


def _has_validation_issue(validation, code: str) -> bool:
    return any(issue.code == code and issue.severity == "error" for issue in validation.issues)


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = f" {str(text).lower()} "
    return any(term in lower for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
