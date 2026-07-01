from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils import format_elapsed


@dataclass
class StageTiming:
    name: str
    elapsed_seconds: float
    count: int | None = None
    notes: str = ""


@dataclass
class BenchmarkResult:
    command_label: str
    candidates_path: str
    total_elapsed_seconds: float
    stage_timings: list[StageTiming] = field(default_factory=list)
    peak_memory_mb: float | None = None
    output_csv: str | None = None
    output_xlsx: str | None = None
    row_count: int | None = None
    validation_passed: bool = False
    warnings: list[str] = field(default_factory=list)


def now_timer() -> float:
    return time.perf_counter()


def measure_peak_memory_mb() -> float | None:
    try:
        import resource
    except ImportError:
        return None
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (AttributeError, OSError, ValueError):
        return None
    if usage <= 0:
        return None
    if sys.platform == "darwin":
        return usage / (1024 * 1024)
    return usage / 1024


def format_benchmark_markdown(result: BenchmarkResult) -> str:
    under_target = result.total_elapsed_seconds <= 300
    lines = [
        "# Submission Benchmark",
        "",
        f"- Command: `{result.command_label}`",
        f"- Candidates: `{result.candidates_path}`",
        f"- Total runtime: {format_elapsed(result.total_elapsed_seconds)}",
        f"- Under 5 minutes: {under_target}",
        f"- Validation passed: {result.validation_passed}",
        f"- Output CSV: `{result.output_csv}`" if result.output_csv else "- Output CSV: not written",
        f"- Output XLSX: `{result.output_xlsx}`" if result.output_xlsx else "- Output XLSX: not written",
        f"- Row count: {result.row_count if result.row_count is not None else 'unknown'}",
    ]
    if result.peak_memory_mb is not None:
        lines.append(f"- Peak memory: {result.peak_memory_mb:.1f} MB")
    lines.extend(["", "## Stage Timings", "", "| Stage | Elapsed | Count | Notes |", "| --- | ---: | ---: | --- |"])
    for stage in result.stage_timings:
        count = "" if stage.count is None else str(stage.count)
        lines.append(f"| {stage.name} | {format_elapsed(stage.elapsed_seconds)} | {count} | {stage.notes} |")
    if result.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines) + "\n"


def stage_to_dict(stage: StageTiming) -> dict[str, Any]:
    return {
        "name": stage.name,
        "elapsed_seconds": stage.elapsed_seconds,
        "count": stage.count,
        "notes": stage.notes,
    }
