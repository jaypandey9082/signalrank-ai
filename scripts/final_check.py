from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTECTED_IGNORES = (
    "candidates.jsonl",
    "candidates.jsonl.gz",
    "outputs/submission.csv",
    "outputs/submission.xlsx",
)
REQUIRED_FILES = (
    "README.md",
    "submission_metadata.yaml",
    "FINAL_SUBMISSION_CHECKLIST.md",
    "SUBMISSION_PACKET.md",
    "DEPLOYMENT.md",
    "DEMO_SCRIPT.md",
    "deck/approach_deck.md",
    "deck/approach_deck.html",
    "sandbox/app.py",
    "requirements.txt",
)


@dataclass
class CheckResult:
    passed: bool
    code: str
    message: str


def run_final_checks(
    root: str | Path = ROOT,
    csv_path: str | Path | None = None,
    xlsx_path: str | Path | None = None,
    candidates_path: str | Path | None = None,
    skip_validator: bool = False,
    skip_audit: bool = False,
) -> list[CheckResult]:
    root_path = Path(root)
    checks: list[CheckResult] = []
    for rel_path in REQUIRED_FILES:
        checks.append(_exists(root_path / rel_path, "required_file", f"Required file exists: {rel_path}"))
    checks.append(_contains(root_path / "requirements.txt", "streamlit", "requirements_streamlit", "requirements.txt includes streamlit"))
    checks.extend(_gitignore_checks(root_path))
    pdf = root_path / "deck/SignalRank_AI_Approach_Deck.pdf"
    if pdf.exists():
        checks.append(CheckResult(pdf.stat().st_size < 5 * 1024 * 1024, "deck_pdf_size", "Deck PDF exists and is under 5 MB."))
    else:
        checks.append(CheckResult(True, "deck_pdf_missing", "Deck PDF missing; use deck HTML and manual Print -> Save as PDF."))

    if csv_path:
        checks.append(_exists(_resolve(root_path, csv_path), "csv_exists", f"CSV exists: {csv_path}"))
    if xlsx_path:
        checks.append(_exists(_resolve(root_path, xlsx_path), "xlsx_exists", f"XLSX exists: {xlsx_path}"))
    if candidates_path:
        checks.append(_exists(_resolve(root_path, candidates_path), "candidates_exists", f"Candidates file exists locally: {candidates_path}"))

    if csv_path and not skip_validator:
        checks.append(_run_validator(root_path, _resolve(root_path, csv_path)))
    if csv_path and xlsx_path and candidates_path and not skip_audit:
        checks.append(_run_audit(root_path, _resolve(root_path, csv_path), _resolve(root_path, xlsx_path), _resolve(root_path, candidates_path)))
    return checks


def format_checks(checks: list[CheckResult]) -> str:
    lines = ["Final Check Summary", "==================="]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"[{status}] {check.code}: {check.message}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run final packaging checks for SignalRank AI.")
    parser.add_argument("--candidates")
    parser.add_argument("--csv")
    parser.add_argument("--xlsx")
    parser.add_argument("--skip-validator", action="store_true")
    parser.add_argument("--skip-audit", action="store_true")
    args = parser.parse_args()

    checks = run_final_checks(
        ROOT,
        csv_path=args.csv,
        xlsx_path=args.xlsx,
        candidates_path=args.candidates,
        skip_validator=args.skip_validator,
        skip_audit=args.skip_audit,
    )
    print(format_checks(checks))
    return 0 if all(check.passed for check in checks) else 1


def _exists(path: Path, code: str, message: str) -> CheckResult:
    return CheckResult(path.exists(), code, message)


def _contains(path: Path, needle: str, code: str, message: str) -> CheckResult:
    if not path.exists():
        return CheckResult(False, code, message)
    return CheckResult(needle in path.read_text(encoding="utf-8"), code, message)


def _gitignore_checks(root: Path) -> list[CheckResult]:
    path = root / ".gitignore"
    if not path.exists():
        return [CheckResult(False, "gitignore_exists", ".gitignore exists")]
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    return [
        CheckResult(entry in lines, "gitignore_entry", f".gitignore protects {entry}")
        for entry in PROTECTED_IGNORES
    ]


def _run_validator(root: Path, csv_path: Path) -> CheckResult:
    validator = root / "validate_submission.py"
    if not validator.exists():
        return CheckResult(True, "external_validator_skipped", "validate_submission.py not present; skipped.")
    completed = subprocess.run([sys.executable, str(validator), str(csv_path)], cwd=root, check=False, capture_output=True, text=True)
    return CheckResult(completed.returncode == 0, "external_validator", "External validator passes.")


def _run_audit(root: Path, csv_path: Path, xlsx_path: Path, candidates_path: Path) -> CheckResult:
    audit = root / "audit_submission.py"
    if not audit.exists():
        return CheckResult(True, "audit_skipped", "audit_submission.py not present; skipped.")
    completed = subprocess.run(
        [
            sys.executable,
            str(audit),
            "--csv",
            str(csv_path),
            "--xlsx",
            str(xlsx_path),
            "--candidates",
            str(candidates_path),
            "--report-out",
            "outputs/submission_audit.md",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return CheckResult(completed.returncode == 0, "repo_audit", "Submission audit passes.")


def _resolve(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


if __name__ == "__main__":
    raise SystemExit(main())
