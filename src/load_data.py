from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from typing import Any, TextIO


class CandidateDataError(Exception):
    """Raised when a candidate input file cannot be read safely."""


def iter_candidates(path: str | Path) -> Iterator[dict[str, Any]]:
    """Stream candidates from JSON, JSONL, or JSONL.GZ files."""
    file_path = _validate_path(path)

    if file_path.suffix == ".json":
        data = _read_json_file(file_path)
        if isinstance(data, dict):
            yield data
            return
        if isinstance(data, list):
            for index, item in enumerate(data):
                if not isinstance(item, dict):
                    raise CandidateDataError(
                        f"Invalid candidate in {file_path} at index {index}: "
                        "expected a JSON object."
                    )
                yield item
            return
        raise CandidateDataError(
            f"{file_path} must contain a candidate object or a list of candidate objects."
        )

    yield from _iter_jsonl_records(file_path)


def load_candidates(path: str | Path, limit: int | None = None) -> list[dict[str, Any]]:
    """Load candidates into memory, optionally limiting the number of records."""
    candidates = iter_candidates(path)
    if limit is not None:
        if limit < 0:
            raise CandidateDataError("limit must be greater than or equal to 0.")
        return list(islice(candidates, limit))
    return list(candidates)


def _validate_path(path: str | Path) -> Path:
    file_path = Path(path)
    if not file_path.exists():
        raise CandidateDataError(f"Candidate file not found: {file_path}")
    if not file_path.is_file():
        raise CandidateDataError(f"Candidate path is not a file: {file_path}")
    if not (file_path.suffix in {".json", ".jsonl"} or _is_jsonl_gz(file_path)):
        raise CandidateDataError(
            f"Unsupported candidate file extension for {file_path}. "
            "Use .json, .jsonl, or .jsonl.gz."
        )
    return file_path


def _read_json_file(file_path: Path) -> Any:
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise CandidateDataError(f"Invalid JSON in {file_path}: {exc.msg}") from exc
    except OSError as exc:
        raise CandidateDataError(f"Could not read {file_path}: {exc}") from exc


def _iter_jsonl_records(file_path: Path) -> Iterator[dict[str, Any]]:
    try:
        with _open_text(file_path) as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    candidate = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise CandidateDataError(
                        f"Invalid JSON in {file_path} at line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(candidate, dict):
                    raise CandidateDataError(
                        f"Invalid candidate in {file_path} at line {line_number}: "
                        "expected a JSON object."
                    )
                yield candidate
    except OSError as exc:
        raise CandidateDataError(f"Could not read {file_path}: {exc}") from exc


def _open_text(file_path: Path) -> TextIO:
    if _is_jsonl_gz(file_path):
        return gzip.open(file_path, "rt", encoding="utf-8")
    return file_path.open("r", encoding="utf-8")


def _is_jsonl_gz(file_path: Path) -> bool:
    return file_path.name.endswith(".jsonl.gz")
