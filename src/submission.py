from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.performance import StageTiming, now_timer
from src.ranking import RankedPreviewRow, rank_candidates_preview
from src.ranking_quality import evaluate_ranking_quality
from src.reasoning import clean_reason_text, generate_reasoning_for_row
from src.reasoning_quality import evaluate_reasoning_quality
from src.utils import round_score


@dataclass
class SubmissionRow:
    candidate_id: str
    rank: int
    score: float
    reasoning: str


@dataclass
class SubmissionBuildResult:
    total_seen: int
    valid_count: int
    ranked_count: int
    submitted_count: int
    skipped_invalid_count: int
    scoring_error_count: int
    elapsed_seconds: float
    rows: list[SubmissionRow]
    ranking_quality_summary: str
    reasoning_quality_summary: str
    warnings: list[str]
    debug_rows: list[dict[str, Any]]
    stage_timings: list[StageTiming] | None = None


def build_submission_rows(
    candidates_path: str | Path,
    top_k: int = 100,
    limit: int | None = None,
    allow_partial: bool = False,
) -> SubmissionBuildResult:
    if top_k != 100 and not allow_partial:
        raise ValueError("Final submissions must use top_k=100. Use allow_partial=True for tests/debug.")
    if limit is not None and not allow_partial:
        raise ValueError("Final submissions must use the full candidate pool. Use allow_partial=True with --limit.")

    started = now_timer()
    ranking_result = rank_candidates_preview(candidates_path, top_k=top_k, limit=limit)
    if len(ranking_result.rows) < top_k:
        raise ValueError(f"Could only produce {len(ranking_result.rows)} rows; expected {top_k}.")

    reasoning_started = now_timer()
    reasonings = []
    reasoning_by_id: dict[str, str] = {}
    warnings = list(ranking_result.warnings)
    for row in ranking_result.rows:
        try:
            reasoning = generate_reasoning_for_row(row)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            warnings.append(f"{row.candidate_id}: reasoning failed with {exc.__class__.__name__}")
            continue
        reasonings.append(reasoning)
        reasoning_by_id[row.candidate_id] = clean_reason_text(reasoning.reasoning)
    reasoning_elapsed = now_timer() - reasoning_started

    quality_started = now_timer()
    ranking_quality = evaluate_ranking_quality(ranking_result.rows)
    reasoning_quality = evaluate_reasoning_quality(ranking_result.rows, reasonings)
    warnings.extend(ranking_quality.warnings)
    warnings.extend(f"{issue.candidate_id}: {issue.issue_code}" for issue in reasoning_quality.issues[:20])
    quality_elapsed = now_timer() - quality_started

    rows_started = now_timer()
    rows: list[SubmissionRow] = []
    for rank, row in enumerate(ranking_result.rows, start=1):
        reasoning = reasoning_by_id.get(row.candidate_id, "")
        if not reasoning:
            if allow_partial:
                reasoning = "Lower-confidence match with limited available reasoning evidence."
            else:
                raise ValueError(f"Missing reasoning for {row.candidate_id}.")
        rows.append(
            SubmissionRow(
                candidate_id=row.candidate_id,
                rank=rank,
                score=round_score(row.final_score_preview, 6),
                reasoning=reasoning,
            )
        )

    if len(rows) < top_k:
        raise ValueError(f"Could only produce {len(rows)} submission rows; expected {top_k}.")
    rows_elapsed = now_timer() - rows_started

    elapsed = now_timer() - started
    result = SubmissionBuildResult(
        total_seen=ranking_result.total_seen,
        valid_count=ranking_result.valid_count,
        ranked_count=ranking_result.ranked_count,
        submitted_count=len(rows),
        skipped_invalid_count=ranking_result.skipped_invalid_count,
        scoring_error_count=ranking_result.scoring_error_count,
        elapsed_seconds=elapsed,
        rows=rows,
        ranking_quality_summary=ranking_quality.summary,
        reasoning_quality_summary=reasoning_quality.summary,
        warnings=warnings,
        debug_rows=[],
        stage_timings=[
            *ranking_result.stage_timings,
            StageTiming("reasoning", reasoning_elapsed, len(reasonings), "generated final reasoning for ranked rows"),
            StageTiming("quality_checks", quality_elapsed, len(rows), "ranking and reasoning quality checks"),
            StageTiming("submission_rows", rows_elapsed, len(rows), "final row conversion"),
        ],
    )
    result.debug_rows = build_submission_debug_rows(result, ranking_result.rows)
    return result


def submission_rows_to_dicts(rows: list[SubmissionRow]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": row.candidate_id,
            "rank": row.rank,
            "score": row.score,
            "reasoning": row.reasoning,
        }
        for row in rows
    ]


def build_submission_debug_rows(
    result: SubmissionBuildResult,
    ranked_rows: list[RankedPreviewRow] | None = None,
) -> list[dict[str, Any]]:
    ranked_by_id = {row.candidate_id: row for row in ranked_rows or []}
    debug_rows: list[dict[str, Any]] = []
    for row in result.rows:
        ranked = ranked_by_id.get(row.candidate_id)
        debug_rows.append(
            {
                "rank": row.rank,
                "candidate_id": row.candidate_id,
                "score": row.score,
                "reasoning": row.reasoning,
                "title": ranked.title if ranked else "",
                "years_of_experience": ranked.years_of_experience if ranked else "",
                "location": ranked.location if ranked else "",
                "static_fit_score": ranked.static_fit_score if ranked else "",
                "redrob_availability_score": ranked.redrob_availability_score if ranked else "",
                "trap_total_penalty": ranked.trap_total_penalty if ranked else "",
                "applied_cap_codes": ranked.applied_cap_codes if ranked else "",
                "debug_summary": ranked.debug_summary if ranked else "",
            }
        )
    return debug_rows
