# Final Submission Workflow

## What Section 10 adds

Section 10 adds final CSV/XLSX export and validation for challenge-ready submission files.

## Final output columns

The final CSV uses exactly:

```text
candidate_id,rank,score,reasoning
```

## Why CSV and XLSX are both generated

CSV is the reproducible source of truth and is used by validators. XLSX is generated from the same rows for portal upload if required.

## Official final command

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

## Optional XLSX/report command

```bash
python generate_submission.py --candidates ./candidates.jsonl --out ./outputs/submission.csv --xlsx ./outputs/submission.xlsx --report-out ./outputs/submission_run_report.md
```

## Safety checks

- No partial data unless `--allow-partial` is explicit.
- Exact top 100 for final runs.
- Monotonic scores.
- Unique candidate IDs and ranks.
- Non-empty factual reasoning.
- Duplicate and format checks before writing final output.
- Optional bundled validator integration.

## What not to submit

- `sample_candidates` output.
- Debug CSV files.
- Ranking preview CSV files.
- Reasoning preview CSV files.
- Partial smoke-test submission files.

## Final notes

The full dataset should not be committed. Generated final outputs are ignored by git.
