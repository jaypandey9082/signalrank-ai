from __future__ import annotations

import json

from benchmark_submission import build_parser, run_one
from src.performance import BenchmarkResult, StageTiming, format_benchmark_markdown, measure_peak_memory_mb
from tests.test_scoring import make_keyword_stuffer, make_strong_candidate


def test_benchmark_markdown_contains_runtime():
    result = BenchmarkResult(
        command_label="tiny",
        candidates_path="data/sample.json",
        total_elapsed_seconds=1.25,
        stage_timings=[StageTiming("stage", 0.5, 3, "ok")],
        peak_memory_mb=12.0,
        output_csv="out.csv",
        output_xlsx=None,
        row_count=3,
        validation_passed=True,
        warnings=[],
    )

    text = format_benchmark_markdown(result)

    assert "Total runtime" in text
    assert "Under 5 minutes" in text


def test_measure_peak_memory_does_not_crash():
    value = measure_peak_memory_mb()

    assert value is None or value > 0


def test_fast_benchmark_runs_on_tiny_data(tmp_path):
    path = tmp_path / "candidates.json"
    candidates = [make_strong_candidate(), make_keyword_stuffer(), make_strong_candidate()]
    candidates[2]["candidate_id"] = "CAND_0000103"
    path.write_text(json.dumps(candidates), encoding="utf-8")
    out = tmp_path / "benchmark.csv"
    args = build_parser().parse_args(
        [
            "--candidates",
            str(path),
            "--top-k",
            "3",
            "--allow-partial",
            "--mode",
            "csv-only",
            "--out",
            str(out),
        ]
    )

    result = run_one(args, out, None, 1)

    assert result.validation_passed
    assert result.row_count == 3
    assert out.exists()
