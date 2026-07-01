from __future__ import annotations

import csv
import gzip
import io
import json
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.export import write_submission_xlsx
from src.submission import SubmissionRow, build_submission_rows, submission_rows_to_dicts
from src.submission_validator import (
    format_submission_validation_markdown,
    format_submission_validation_report,
    validate_submission_rows,
)


DEMO_MAX_CANDIDATES = 100
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class SandboxRunResult:
    rows: list[dict[str, Any]]
    debug_rows: list[dict[str, Any]]
    candidate_count: int
    processed_count: int
    selected_top_k: int
    effective_top_k: int
    validation_is_valid: bool
    validation_error_count: int
    validation_warning_count: int
    validation_text: str
    validation_markdown: str
    csv_bytes: bytes
    xlsx_bytes: bytes
    report_markdown: str
    elapsed_seconds: float
    warnings: list[str]


def load_demo_sample() -> list[dict[str, Any]]:
    candidates = _load_json_candidates(PROJECT_ROOT / "sandbox/sample_candidates_demo.json")
    if candidates:
        return candidates
    return _load_json_candidates(PROJECT_ROOT / "data/sample_candidates_tiny.json")


def parse_uploaded_candidate_file(file_name: str, file_bytes: bytes) -> list[dict[str, Any]]:
    name = file_name.lower()
    if name.endswith(".gz"):
        try:
            text = gzip.decompress(file_bytes).decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"Could not read compressed upload: {exc}") from exc
    else:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Upload must be UTF-8 text or gzip-compressed UTF-8: {exc}") from exc

    if name.endswith(".json") or name.endswith(".json.gz"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON upload: {exc.msg}") from exc
        return _coerce_candidate_payload(data)
    if name.endswith(".jsonl") or name.endswith(".jsonl.gz") or name.endswith(".gz"):
        return _parse_jsonl_text(text)
    raise ValueError("Unsupported upload type. Use .json, .jsonl, or .jsonl.gz.")


def cap_candidates_for_demo(
    candidates: list[dict[str, Any]],
    max_candidates: int = DEMO_MAX_CANDIDATES,
) -> tuple[list[dict[str, Any]], list[str]]:
    if max_candidates < 1:
        raise ValueError("max_candidates must be at least 1.")
    warnings: list[str] = []
    if len(candidates) > max_candidates:
        warnings.append(
            f"Uploaded sample has {len(candidates)} candidates; demo mode processed the first {max_candidates} only."
        )
    return candidates[:max_candidates], warnings


def write_temp_candidates_json(candidates: list[dict[str, Any]]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
    with handle:
        json.dump(candidates, handle)
    return Path(handle.name)


def run_demo_ranking(
    candidates: list[dict[str, Any]],
    top_k: int = 20,
    max_candidates: int = DEMO_MAX_CANDIDATES,
) -> SandboxRunResult:
    if not candidates:
        raise ValueError("No candidates found in the sample.")
    capped_candidates, warnings = cap_candidates_for_demo(candidates, max_candidates=max_candidates)
    selected_top_k = max(1, int(top_k))
    active_top_k = max(1, min(selected_top_k, len(capped_candidates), max_candidates))
    if active_top_k != selected_top_k:
        warnings.append(
            f"Only {len(capped_candidates)} candidates loaded, so Top K was capped to {active_top_k} for this demo."
        )

    temp_path = write_temp_candidates_json(capped_candidates)
    started = time.perf_counter()
    try:
        result = build_submission_rows(temp_path, top_k=active_top_k, allow_partial=True)
    finally:
        temp_path.unlink(missing_ok=True)

    validation = validate_submission_rows(result.rows, expected_count=len(result.rows))
    csv_bytes = submission_rows_to_csv_bytes(result.rows)
    xlsx_bytes = submission_rows_to_xlsx_bytes(result.rows)
    elapsed = time.perf_counter() - started
    combined_warnings = warnings + result.warnings
    rows = submission_rows_to_dicts(result.rows)
    return SandboxRunResult(
        rows=rows,
        debug_rows=result.debug_rows,
        candidate_count=len(candidates),
        processed_count=len(capped_candidates),
        selected_top_k=selected_top_k,
        effective_top_k=active_top_k,
        validation_is_valid=validation.is_valid,
        validation_error_count=validation.error_count,
        validation_warning_count=validation.warning_count,
        validation_text=format_submission_validation_report(validation),
        validation_markdown=format_submission_validation_markdown(validation),
        csv_bytes=csv_bytes,
        xlsx_bytes=xlsx_bytes,
        report_markdown=_demo_report_markdown(
            rows=rows,
            candidate_count=len(candidates),
            processed_count=len(capped_candidates),
            selected_top_k=selected_top_k,
            effective_top_k=active_top_k,
            validation_is_valid=validation.is_valid,
            validation_error_count=validation.error_count,
            validation_warning_count=validation.warning_count,
            elapsed_seconds=elapsed,
            warnings=combined_warnings,
        ),
        elapsed_seconds=elapsed,
        warnings=combined_warnings,
    )


def submission_rows_to_csv_bytes(rows: list[SubmissionRow]) -> bytes:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=["candidate_id", "rank", "score", "reasoning"])
    writer.writeheader()
    writer.writerows(submission_rows_to_dicts(rows))
    return handle.getvalue().encode("utf-8")


def submission_rows_to_xlsx_bytes(rows: list[SubmissionRow]) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        write_submission_xlsx(rows, temp_path)
        return temp_path.read_bytes()
    finally:
        temp_path.unlink(missing_ok=True)


def shorten_reasoning_for_table(reasoning: str, max_chars: int = 180) -> str:
    text = " ".join(str(reasoning or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rsplit(" ", 1)[0].rstrip() + "..."


def candidate_preview_rows(candidates: list[dict[str, Any]], max_rows: int = 10) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for candidate in candidates[:max_rows]:
        profile = candidate.get("profile") if isinstance(candidate.get("profile"), dict) else {}
        preview.append(
            {
                "candidate_id": candidate.get("candidate_id", ""),
                "title": profile.get("current_title", ""),
                "location": profile.get("location", ""),
                "years_of_experience": profile.get("years_of_experience", ""),
            }
        )
    return preview


def _load_json_candidates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return _coerce_candidate_payload(data)


def _coerce_candidate_payload(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    raise ValueError("Candidate file must contain a candidate object or a list of candidate objects.")


def _parse_jsonl_text(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_number}: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Invalid JSONL at line {line_number}: expected an object.")
        candidates.append(record)
    if not candidates:
        raise ValueError("No candidates found in JSONL upload.")
    return candidates


def _demo_report_markdown(
    *,
    rows: list[dict[str, Any]],
    candidate_count: int,
    processed_count: int,
    selected_top_k: int,
    effective_top_k: int,
    validation_is_valid: bool,
    validation_error_count: int,
    validation_warning_count: int,
    elapsed_seconds: float,
    warnings: list[str],
) -> str:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    validation_label = "passed" if validation_is_valid else "failed"
    lines = [
        "# SignalRank AI Demo Report",
        "",
        f"- Generated at: {generated_at}",
        f"- Candidate count loaded: {candidate_count}",
        f"- Candidate count processed: {processed_count}",
        f"- Selected Top K: {selected_top_k}",
        f"- Effective Top K: {effective_top_k}",
        f"- Runtime seconds: {elapsed_seconds:.3f}",
        f"- Validation summary: {validation_label} ({validation_error_count} errors, {validation_warning_count} warnings)",
        "",
        "## Warnings",
    ]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    lines.extend(["", "## Ranked Preview", "", "| rank | candidate_id | score | reasoning |", "|---:|---|---:|---|"])
    for row in rows[:10]:
        reasoning = " ".join(str(row.get("reasoning", "")).split())
        if len(reasoning) > 120:
            reasoning = reasoning[:117].rstrip() + "..."
        reasoning = reasoning.replace("|", "\\|")
        lines.append(
            f"| {row.get('rank', '')} | {row.get('candidate_id', '')} | {row.get('score', '')} | {reasoning} |"
        )
    return "\n".join(lines) + "\n"
