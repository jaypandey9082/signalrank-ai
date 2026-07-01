from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from generate_submission import _find_external_validator
from src.export import write_submission_csv, write_submission_xlsx
from src.performance import BenchmarkResult, StageTiming, format_benchmark_markdown, measure_peak_memory_mb, now_timer
from src.reproducibility import compare_csv_files
from src.runtime_report import build_runtime_report, write_runtime_report
from src.submission import build_submission_rows
from src.submission_validator import validate_submission_rows
from src.utils import ensure_parent_dir, format_elapsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark SignalRank AI submission generation.")
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--mode", choices=["csv-only", "csv-report", "csv-xlsx", "csv-xlsx-report"], default="csv-only")
    parser.add_argument("--out", default="outputs/benchmark_submission.csv")
    parser.add_argument("--xlsx")
    parser.add_argument("--report-out", default="outputs/benchmark_report.md")
    parser.add_argument("--top-k", type=int, default=100)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--compare-determinism", action="store_true")
    parser.add_argument("--skip-external-validator", action="store_true")
    parser.add_argument("--run-external-validator", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    outputs: list[Path] = []
    reports: list[BenchmarkResult] = []
    repeat_count = max(args.repeat, 1)

    for index in range(1, repeat_count + 1):
        csv_path = _repeat_path(Path(args.out), index, repeat_count)
        xlsx_path = _repeat_path(Path(args.xlsx), index, repeat_count) if args.xlsx else _default_xlsx(csv_path, args.mode)
        report = run_one(args, csv_path, xlsx_path, index)
        reports.append(report)
        outputs.append(csv_path)
        print(
            f"Benchmark run {index}/{repeat_count}: "
            f"{format_elapsed(report.total_elapsed_seconds)}, validation={report.validation_passed}, csv={csv_path}"
        )

    if args.compare_determinism and repeat_count >= 2:
        comparison = compare_csv_files(outputs[0], outputs[1])
        if not comparison["same_hash"]:
            print(f"Determinism check failed: {comparison['first_difference_summary']}", file=sys.stderr)
            return 1
        reports[-1].warnings.append(f"Determinism check passed: {comparison['hash_a']}")

    if args.report_out:
        ensure_parent_dir(args.report_out)
        Path(args.report_out).write_text(_combined_report_markdown(reports), encoding="utf-8")
        print(f"Wrote benchmark report to {args.report_out}")

    return 0 if all(report.validation_passed for report in reports) else 1


def run_one(args: argparse.Namespace, csv_path: Path, xlsx_path: Path | None, run_index: int) -> BenchmarkResult:
    started = now_timer()
    stage_timings: list[StageTiming] = []

    build_started = now_timer()
    result = build_submission_rows(
        args.candidates,
        top_k=args.top_k,
        limit=args.limit,
        allow_partial=args.allow_partial,
    )
    stage_timings.extend(result.stage_timings or [])
    stage_timings.append(StageTiming("build_submission_rows_total", now_timer() - build_started, result.submitted_count))

    validation_started = now_timer()
    validation = validate_submission_rows(result.rows, expected_count=len(result.rows) if args.allow_partial else 100)
    stage_timings.append(StageTiming("internal_validation", now_timer() - validation_started, len(result.rows)))
    if not validation.is_valid:
        return BenchmarkResult(
            command_label=f"benchmark run {run_index}",
            candidates_path=args.candidates,
            total_elapsed_seconds=now_timer() - started,
            stage_timings=stage_timings,
            peak_memory_mb=measure_peak_memory_mb(),
            output_csv=str(csv_path),
            output_xlsx=str(xlsx_path) if xlsx_path else None,
            row_count=len(result.rows),
            validation_passed=False,
            warnings=[f"Internal validation failed with {validation.error_count} errors."],
        )

    csv_started = now_timer()
    write_submission_csv(result.rows, csv_path)
    stage_timings.append(StageTiming("csv_export", now_timer() - csv_started, len(result.rows)))

    wrote_xlsx = False
    if xlsx_path and args.mode in {"csv-xlsx", "csv-xlsx-report"}:
        xlsx_started = now_timer()
        write_submission_xlsx(result.rows, xlsx_path)
        wrote_xlsx = True
        stage_timings.append(StageTiming("xlsx_export", now_timer() - xlsx_started, len(result.rows)))

    if args.mode in {"csv-report", "csv-xlsx-report"}:
        report_started = now_timer()
        runtime_report = build_runtime_report(result, args.candidates, csv_path, xlsx_path if wrote_xlsx else None, validation)
        write_runtime_report(runtime_report, Path(args.report_out).with_suffix(f".run{run_index}.md"))
        stage_timings.append(StageTiming("runtime_report", now_timer() - report_started, len(result.rows)))

    warnings = list(result.warnings)
    if args.run_external_validator and not args.skip_external_validator and not args.allow_partial:
        external_started = now_timer()
        output = _run_external_validator(csv_path)
        stage_timings.append(StageTiming("external_validator", now_timer() - external_started, len(result.rows)))
        warnings.append(output.strip())

    return BenchmarkResult(
        command_label=f"benchmark run {run_index} ({args.mode})",
        candidates_path=args.candidates,
        total_elapsed_seconds=now_timer() - started,
        stage_timings=stage_timings,
        peak_memory_mb=measure_peak_memory_mb(),
        output_csv=str(csv_path),
        output_xlsx=str(xlsx_path) if wrote_xlsx and xlsx_path else None,
        row_count=len(result.rows),
        validation_passed=validation.is_valid,
        warnings=warnings,
    )


def _run_external_validator(csv_path: str | Path) -> str:
    validator = _find_external_validator()
    if validator is None:
        return "External validate_submission.py not found; skipped."
    completed = subprocess.run([sys.executable, str(validator), str(csv_path)], check=False, capture_output=True, text=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    return "External validator passed:\n" + output if completed.returncode == 0 else "External validator failed:\n" + output


def _combined_report_markdown(reports: list[BenchmarkResult]) -> str:
    lines: list[str] = []
    for index, report in enumerate(reports, start=1):
        if index > 1:
            lines.append("\n---\n")
        lines.append(format_benchmark_markdown(report))
    return "\n".join(lines)


def _repeat_path(path: Path, index: int, repeat_count: int) -> Path:
    if repeat_count <= 1:
        return path
    return path.with_name(f"{path.stem}_run{index}{path.suffix}")


def _default_xlsx(csv_path: Path, mode: str) -> Path | None:
    if mode not in {"csv-xlsx", "csv-xlsx-report"}:
        return None
    return csv_path.with_suffix(".xlsx")


if __name__ == "__main__":
    raise SystemExit(main())
