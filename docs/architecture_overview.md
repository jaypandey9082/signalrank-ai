# Architecture Overview

## Pipeline

```text
candidates.jsonl
  |
  v
iter_candidates
  |
  v
schema/basic validation
  |
  v
feature extraction
  |
  v
static fit scoring
  |
  v
Redrob behavior scoring
  |
  v
trap penalty scoring
  |
  v
combined ranking
  |
  v
reasoning generator
  |
  v
submission.csv / submission.xlsx
```

## Module Map

- `src/load_data.py`: JSON, JSONL, and JSONL.GZ candidate streaming.
- `src/features.py`: profile, career, skills, education, Redrob, and diagnostic feature extraction.
- `src/scoring.py`: static candidate-job fit scoring.
- `src/redrob_scoring.py`: platform behavior and hireability scoring.
- `src/trap_penalties.py`: keyword-stuffing, inconsistency, and honeypot-style penalty signals.
- `src/combined_scoring.py`: static score, behavior multiplier, trap multiplier, and guardrail caps.
- `src/ranking.py`: deterministic ranking and top-k selection.
- `src/reasoning.py`: evidence-based final reasoning.
- `src/submission.py`: final row builder.
- `sandbox/app.py`: small-sample Streamlit demo.

## Reproducibility

The official command is:

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

The ranking path is deterministic, CPU-only, and uses no hosted API calls.
