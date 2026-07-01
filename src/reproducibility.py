from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows_sha256(rows: list[dict]) -> str:
    normalized = [
        {key: _normalize_value(row.get(key)) for key in sorted(row)}
        for row in rows
    ]
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compare_csv_files(path_a: str | Path, path_b: str | Path) -> dict[str, Any]:
    rows_a = _read_csv(path_a)
    rows_b = _read_csv(path_b)
    hash_a = file_sha256(path_a)
    hash_b = file_sha256(path_b)
    return {
        "same_hash": hash_a == hash_b,
        "hash_a": hash_a,
        "hash_b": hash_b,
        "row_count_a": len(rows_a),
        "row_count_b": len(rows_b),
        "first_difference_summary": _first_difference(rows_a, rows_b),
    }


def assert_deterministic_outputs(path_a: str | Path, path_b: str | Path) -> None:
    comparison = compare_csv_files(path_a, path_b)
    if not comparison["same_hash"]:
        raise AssertionError(f"CSV outputs differ: {comparison['first_difference_summary']}")


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _first_difference(rows_a: list[dict], rows_b: list[dict]) -> str:
    if len(rows_a) != len(rows_b):
        return f"row count differs: {len(rows_a)} != {len(rows_b)}"
    for index, (row_a, row_b) in enumerate(zip(rows_a, rows_b), start=1):
        if row_a != row_b:
            return f"first difference at row {index}: {row_a} != {row_b}"
    return ""


def _normalize_value(value: object) -> str:
    return "" if value is None else str(value)
