# Submission QA and Performance

## Why this section was needed

Section 10 produced valid submission files, but the full CSV/XLSX/report command took 10m 53.6s. Format validation alone is not enough for the challenge constraints, so Section 10.5 separates the official CSV path from optional review artifacts and adds timing, determinism, and repo hygiene checks.

## What we benchmark

- CSV-only final command
- Optional XLSX/report generation
- External validator when explicitly requested
- Deterministic repeat runs
- Repo and dependency audit

## Official fast command

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

## Optional portal XLSX command

```bash
python generate_submission.py --candidates ./candidates.jsonl --out ./outputs/submission.csv --xlsx ./outputs/submission.xlsx --report-out ./outputs/submission_run_report.md
```

## Runtime target

CSV-only should finish under 5 minutes on CPU with no hosted API calls. If it does not, report the exact runtime and the bottleneck rather than claiming compliance.

## What not to submit

- Benchmark files
- Debug CSVs
- Partial outputs
- Sample outputs
- Top-100 manual review notes

The full candidate file and generated final outputs should not be committed.
