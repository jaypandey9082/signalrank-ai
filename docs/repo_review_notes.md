# Repository Review Notes

## Public Repo Boundary

This repository intentionally excludes the full challenge dataset and generated final outputs. The ranker is reproducible from source, but `candidates.jsonl`, final CSV/XLSX files, benchmark outputs, debug CSVs, audit reports, and local submission packets are kept out of git.

## Canonical Reproduction

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

This command produces the canonical CSV format:

```text
candidate_id,rank,score,reasoning
```

## Validation

```bash
python validate_submission.py submission.csv
```

If using the optional output path under `outputs/`, validate `outputs/submission.csv` instead.

## Local-Only Files

- `candidates.jsonl`
- `candidates.jsonl.gz`
- `outputs/*.csv`
- `outputs/*.xlsx`
- generated audit, benchmark, review, and report markdown files
- `submission_packet/`
- `signalrank_submission_packet.zip`

These artifacts may be needed for local reproduction or portal upload, but they should not be committed to the public repository.
