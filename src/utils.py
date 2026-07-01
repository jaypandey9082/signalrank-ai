from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any


def ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def round_score(score: float, digits: int = 6) -> float:
    return round(float(score), digits)


def top_n_by_key(items: list[dict], key: str, n: int, reverse: bool = True) -> list[dict]:
    return sorted(items, key=lambda item: item.get(key, 0), reverse=reverse)[:n]


def safe_mean(values: list[float | int]) -> float:
    return float(mean(values)) if values else 0.0


def bool_rate(values: list[bool]) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if value) / len(values)


def safe_join(values: list[str], sep: str = ", ") -> str:
    return sep.join(value for value in values if value)


def cap_list(values: list, max_items: int = 5) -> list:
    return values[:max_items] if values else []


def parse_float(value: object, default: float | None = None) -> float | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def parse_int(value: object, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return default
        if parsed.is_integer():
            return int(parsed)
    return default


def format_elapsed(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes}m {remainder:.1f}s"


def safe_percent(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def stable_candidate_sort_key(row_or_dict: Any) -> str:
    if isinstance(row_or_dict, dict):
        return str(row_or_dict.get("candidate_id", ""))
    return str(getattr(row_or_dict, "candidate_id", ""))


def sentence_join(sentences: list[str], max_sentences: int = 2) -> str:
    cleaned = [" ".join(sentence.split()).strip() for sentence in sentences if sentence and sentence.strip()]
    return " ".join(cleaned[:max_sentences])


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = " ".join(str(value or "").split()).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output


def shorten_list_text(values: list[str], max_items: int = 3) -> str:
    items = unique_preserve_order(values)[:max_items]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"
