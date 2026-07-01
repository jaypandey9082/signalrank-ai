# Combined Ranking Strategy

## What this section does

Section 8 combines static candidate-job fit, the Redrob hireability multiplier, and the trap penalty multiplier into a ranked preview.

It does not create `submission.csv`, `submission.xlsx`, or final polished candidate reasoning.

## Formula

`combined_score = static_fit_score x behavior_multiplier x trap_penalty_multiplier`

Then guardrail caps are applied.

## Why static fit remains central

Career evidence and role fit matter more than activity or keyword count. A candidate with production ranking, search, retrieval, recommendation, embedding, and evaluation evidence should rank above a candidate who only lists AI tools in a skill section.

## Why behavior is a narrow multiplier

Active and responsive candidates are more hireable, but behavior cannot make a weak profile a top match. The Redrob multiplier is intentionally narrow so availability nudges the ranking without replacing technical fit.

## Why guardrail caps exist

Caps protect top ranks from wrong-role keyword stuffers, weak AI hype, no real retrieval evidence, non-target AI-only profiles, consulting-only histories without product retrieval work, and high trap risk.

Caps are ranking safety checks. They are not normal concerns like a 60-day notice period, and they do not create final rejection labels.

## Ranking quality checks

The preview quality report checks whether the top rows look plausible before final submission work:

- Top 10 should mostly have real retrieval/ranking evidence.
- Top 10 should have zero wrong-role titles.
- Top 100 high/extreme trap rate should stay low.
- Top 100 keyword-stuffing rate should stay low.
- Low-hireability and no-production-evidence counts are surfaced for tuning.

Warnings do not fail the run. They tell us where to tune scoring before final export.

## What comes next

Section 9 generates factual reasoning previews from evidence seeds.

Section 10 will create final CSV/XLSX submission files.
