from __future__ import annotations

import csv
import heapq
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.combined_scoring import combined_scorecard_to_flat_dict, compute_combined_scorecard
from src.load_data import iter_candidates
from src.performance import StageTiming
from src.schema import is_valid_candidate_id, validate_candidate
from src.scoring_config import RANKING_DEFAULT_TOP_K
from src.utils import ensure_parent_dir, format_elapsed, stable_candidate_sort_key


@dataclass
class RankedPreviewRow:
    preview_rank: int
    candidate_id: str
    final_score_preview: float
    final_score_band: str
    title: str
    title_category: str
    years_of_experience: float | None
    location: str
    location_category: str
    static_fit_score: float
    redrob_availability_score: float
    behavior_multiplier: float
    trap_total_penalty: float
    trap_penalty_multiplier: float
    applied_cap_codes: str
    debug_summary: str
    evidence_seeds: list[str]
    flat_debug: dict[str, Any]


@dataclass
class RankingPreviewResult:
    total_seen: int
    valid_count: int
    ranked_count: int
    skipped_invalid_count: int
    scoring_error_count: int
    elapsed_seconds: float
    rows: list[RankedPreviewRow]
    warnings: list[str]
    stage_timings: list[StageTiming] = field(default_factory=list)


def rank_candidates_preview(
    path: str | Path,
    top_k: int = RANKING_DEFAULT_TOP_K,
    limit: int | None = None,
    validation_mode: str = "basic",
    enrich_top_rows: bool = True,
) -> RankingPreviewResult:
    started = time.perf_counter()
    scoring_started = time.perf_counter()
    total_seen = 0
    valid_count = 0
    skipped_invalid_count = 0
    scoring_error_count = 0
    heap: list[tuple[tuple[float, int], int, RankedPreviewRow, dict[str, Any]]] = []
    warnings: list[str] = []
    active_top_k = max(0, top_k)
    sequence = 0

    for candidate in iter_candidates(path):
        if limit is not None and total_seen >= limit:
            break
        total_seen += 1

        if not _candidate_is_valid_for_ranking(candidate, validation_mode):
            skipped_invalid_count += 1
            continue

        valid_count += 1
        try:
            scorecard = _compute_scorecard(candidate, include_evidence=False)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            scoring_error_count += 1
            if len(warnings) < 5:
                candidate_id = candidate.get("candidate_id", "<unknown>")
                warnings.append(f"{candidate_id}: combined scoring failed with {exc.__class__.__name__}")
            continue

        flat = combined_scorecard_to_flat_dict(scorecard)
        row = RankedPreviewRow(
            preview_rank=0,
            candidate_id=scorecard.candidate_id,
            final_score_preview=scorecard.final_score,
            final_score_band=scorecard.final_score_band,
            title=scorecard.title,
            title_category=scorecard.title_category,
            years_of_experience=scorecard.years_of_experience,
            location=scorecard.location,
            location_category=scorecard.location_category,
            static_fit_score=scorecard.static_fit_score,
            redrob_availability_score=scorecard.redrob_availability_score,
            behavior_multiplier=scorecard.behavior_multiplier,
            trap_total_penalty=scorecard.trap_total_penalty,
            trap_penalty_multiplier=scorecard.trap_penalty_multiplier,
            applied_cap_codes=flat.get("applied_cap_codes", ""),
            debug_summary=scorecard.debug_summary,
            evidence_seeds=scorecard.evidence_seeds,
            flat_debug=flat,
        )
        if active_top_k:
            sequence += 1
            heap_item = (_ranking_heap_key(row), sequence, row, candidate)
            if len(heap) < active_top_k:
                heapq.heappush(heap, heap_item)
            elif heap_item[0] > heap[0][0]:
                heapq.heapreplace(heap, heap_item)

    scoring_elapsed = time.perf_counter() - scoring_started
    rows_with_candidates = [(item[2], item[3]) for item in heap]
    rows_with_candidates.sort(key=lambda item: (-item[0].final_score_preview, stable_candidate_sort_key(item[0])))

    enrich_started = time.perf_counter()
    if enrich_top_rows:
        enriched_rows: list[RankedPreviewRow] = []
        for row, candidate in rows_with_candidates:
            try:
                scorecard = _compute_scorecard(candidate, include_evidence=True)
            except (TypeError, ValueError, KeyError, AttributeError):
                enriched_rows.append(row)
                continue
            flat = combined_scorecard_to_flat_dict(scorecard)
            enriched_rows.append(
                RankedPreviewRow(
                    preview_rank=0,
                    candidate_id=scorecard.candidate_id,
                    final_score_preview=scorecard.final_score,
                    final_score_band=scorecard.final_score_band,
                    title=scorecard.title,
                    title_category=scorecard.title_category,
                    years_of_experience=scorecard.years_of_experience,
                    location=scorecard.location,
                    location_category=scorecard.location_category,
                    static_fit_score=scorecard.static_fit_score,
                    redrob_availability_score=scorecard.redrob_availability_score,
                    behavior_multiplier=scorecard.behavior_multiplier,
                    trap_total_penalty=scorecard.trap_total_penalty,
                    trap_penalty_multiplier=scorecard.trap_penalty_multiplier,
                    applied_cap_codes=flat.get("applied_cap_codes", ""),
                    debug_summary=scorecard.debug_summary,
                    evidence_seeds=scorecard.evidence_seeds,
                    flat_debug=flat,
                )
            )
        rows = sorted(enriched_rows, key=lambda row: (-row.final_score_preview, stable_candidate_sort_key(row)))
    else:
        rows = [row for row, _candidate in rows_with_candidates]
    enrich_elapsed = time.perf_counter() - enrich_started

    for index, row in enumerate(rows, start=1):
        row.preview_rank = index
        row.flat_debug["preview_rank"] = index

    elapsed = time.perf_counter() - started
    return RankingPreviewResult(
        total_seen=total_seen,
        valid_count=valid_count,
        ranked_count=len(rows),
        skipped_invalid_count=skipped_invalid_count,
        scoring_error_count=scoring_error_count,
        elapsed_seconds=elapsed,
        rows=rows,
        warnings=warnings,
        stage_timings=[
            StageTiming("loading_scoring_ranking", scoring_elapsed, total_seen, "streamed candidates and kept top_k heap"),
            StageTiming("top_row_enrichment", enrich_elapsed, len(rows), "rebuilt rich evidence for selected rows"),
        ],
    )


def ranked_preview_rows_to_flat_dicts(rows: list[RankedPreviewRow]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        flat = dict(row.flat_debug)
        flat["preview_rank"] = row.preview_rank
        flat["final_score_preview"] = row.final_score_preview
        output.append(flat)
    return output


def write_ranking_preview_csv(rows: list[RankedPreviewRow], out_path: str | Path) -> None:
    output_path = Path(out_path)
    ensure_parent_dir(output_path)
    flat_rows = ranked_preview_rows_to_flat_dicts(rows)
    fieldnames = sorted({key for row in flat_rows for key in row.keys()}) if flat_rows else [
        "preview_rank",
        "candidate_id",
        "final_score_preview",
    ]
    preferred = ["preview_rank", "candidate_id", "final_score_preview", "final_score_band"]
    ordered_fieldnames = preferred + [name for name in fieldnames if name not in preferred]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ordered_fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)


def format_ranking_console_report(result: RankingPreviewResult, max_rows: int = 20) -> str:
    lines = [
        "SignalRank AI Ranking Preview",
        "=============================",
        f"Total candidates seen: {result.total_seen}",
        f"Valid candidates: {result.valid_count}",
        f"Ranked preview rows: {result.ranked_count}",
        f"Skipped invalid candidates: {result.skipped_invalid_count}",
        f"Scoring errors: {result.scoring_error_count}",
        f"Elapsed: {format_elapsed(result.elapsed_seconds)}",
        "",
        "Top preview rows:",
        _format_rows(result.rows[:max_rows]),
    ]
    if result.warnings:
        lines.extend(["", "Warnings:", *[f"- {warning}" for warning in result.warnings]])
    return "\n".join(lines)


def format_ranking_markdown_report(result: RankingPreviewResult, max_rows: int = 50) -> str:
    lines = [
        "# Ranking Preview Report",
        "",
        "This is a ranking preview, not the final challenge submission.",
        "",
        "## Summary",
        "",
        f"- Total candidates seen: {result.total_seen}",
        f"- Valid candidates: {result.valid_count}",
        f"- Ranked preview rows: {result.ranked_count}",
        f"- Skipped invalid candidates: {result.skipped_invalid_count}",
        f"- Scoring errors: {result.scoring_error_count}",
        f"- Elapsed: {format_elapsed(result.elapsed_seconds)}",
        "",
        "## Top Preview Rows",
        _format_rows(result.rows[:max_rows]),
    ]
    if result.warnings:
        lines.extend(["", "## Warnings", *[f"- {warning}" for warning in result.warnings]])
    return "\n".join(lines) + "\n"


def _format_rows(rows: list[RankedPreviewRow]) -> str:
    if not rows:
        return "- None"
    return "\n".join(
        "- "
        f"#{row.preview_rank} {row.candidate_id} | {row.final_score_preview:.4f} | "
        f"{row.final_score_band} | {row.title} | caps={row.applied_cap_codes or 'none'} | "
        f"{row.debug_summary}"
        for row in rows
    )


def _candidate_is_valid_for_ranking(candidate: dict[str, Any], validation_mode: str) -> bool:
    if validation_mode == "strict":
        return validate_candidate(candidate).is_valid
    if not isinstance(candidate, dict):
        return False
    if not is_valid_candidate_id(candidate.get("candidate_id")):
        return False
    return (
        isinstance(candidate.get("profile"), dict)
        and isinstance(candidate.get("career_history"), list)
        and isinstance(candidate.get("skills"), list)
        and isinstance(candidate.get("redrob_signals"), dict)
    )


def _ranking_heap_key(row: RankedPreviewRow) -> tuple[float, int]:
    return (row.final_score_preview, -_candidate_id_number(row.candidate_id))


def _candidate_id_number(candidate_id: str) -> int:
    try:
        return int(candidate_id.split("_", 1)[1])
    except (IndexError, ValueError):
        return 10**12


def _compute_scorecard(candidate: dict[str, Any], include_evidence: bool):
    try:
        return compute_combined_scorecard(
            candidate,
            include_evidence=include_evidence,
            include_matched_signal_terms=False,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        return compute_combined_scorecard(candidate)
