# SignalRank AI

**Explainable Candidate Discovery Engine for the Redrob / India.RUNS Data & AI Challenge**

SignalRank AI is a deterministic, CPU-only candidate ranking system built for the Senior AI Engineer — Founding Team role at Redrob AI. It ranks candidates by real career evidence, retrieval/ranking/search experience, Redrob behavioral signals, trap resistance, and factual reasoning — not by raw AI keyword count.

Final submission output uses exactly:

```text
candidate_id,rank,score,reasoning
```

## Submission Snapshot

| Item | Status |
|---|---|
| Final ranked output | `outputs/submission.csv` and `outputs/submission.xlsx` generated locally |
| Canonical submission format | CSV with `candidate_id,rank,score,reasoning` |
| Portal convenience file | XLSX generated from the same rows as CSV |
| Full dataset run | 100,000 candidates processed |
| Official CSV-only runtime | Around 3m16s-3m23s locally |
| Runtime target | Under 5 minutes |
| Ranking mode | CPU-only |
| Network/API calls during ranking | None |
| Hosted LLM calls during ranking | None |
| Output determinism | Repeated run produced identical SHA-256 |
| External validator | Passed |
| CSV/XLSX parity | Passed |
| Sandbox demo | Small-sample Streamlit demo available locally |
| Full dataset committed | No |

The full `candidates.jsonl` file and generated final outputs are intentionally ignored by git.

## Why SignalRank AI Exists

Most recruiting search systems over-rank candidates who list the right words and under-rank candidates who actually built relevant systems.

Instead of asking “Who has the most AI keywords?”, SignalRank asks: “Who has evidence of building production ranking, search, retrieval, or recommendation systems — and are they reachable and hireable?”

## Core Approach

| Layer | Purpose |
|---|---|
| Static Fit Score | Measures role fit from career history, ranking/search/retrieval evidence, skills, experience, location, and education. |
| Redrob Behavior Multiplier | Uses availability, responsiveness, reliability, logistics, trust, and platform signals as narrow hireability modifiers. |
| Trap Penalty Multiplier | Reduces false positives from wrong-role keyword stuffing, weak AI hype, inconsistencies, and low availability risk. |
| Evidence-Based Reasoning | Generates deterministic, factual explanations from extracted candidate evidence and scorecards. |

```text
combined_score =
  static_fit_score
  × redrob_behavior_multiplier
  × trap_penalty_multiplier
  → guardrail caps
```

## Architecture

```text
candidates.jsonl
  ↓
Streaming data loader
  ↓
Schema-safe parsing
  ↓
Candidate normalization
  ↓
Feature extraction
  ↓
Static fit scoring
  ↓
Redrob behavior scoring
  ↓
Trap / honeypot-style penalty scoring
  ↓
Combined ranking
  ↓
Evidence-based reasoning
  ↓
Validated CSV / XLSX output
```

Main modules:

| Module | Responsibility |
|---|---|
| `src/load_data.py` | Streams JSON, JSONL, and JSONL.GZ candidate files. |
| `src/schema.py` | Keeps parsing schema-safe and tolerant of missing fields. |
| `src/taxonomy.py` | Holds JD-aligned keyword and signal groups. |
| `src/features.py` | Extracts normalized profile, career, skill, education, Redrob, and diagnostic features. |
| `src/scoring.py` | Computes static candidate-role fit. |
| `src/redrob_scoring.py` | Scores behavior and hireability signals. |
| `src/trap_penalties.py` | Applies wrong-role, keyword-stuffing, inconsistency, and honeypot-style penalties. |
| `src/combined_scoring.py` | Combines fit, behavior, penalties, and guardrail caps. |
| `src/ranking.py` | Produces deterministic top-k ranking. |
| `src/reasoning.py` | Generates factual evidence-based reasoning. |
| `src/submission.py` | Builds final submission rows. |
| `src/submission_validator.py` | Validates CSV shape, ranks, scores, IDs, and reasoning. |

## What Makes It Different

### Career evidence beats keyword count

Career descriptions receive more weight than raw skill lists because they show what a candidate actually shipped.

### Skills are trusted only when supported

Skill matches help, but unsupported skill stuffing is capped or penalized when career evidence is weak.

### Redrob signals are used as hireability modifiers

Redrob behavior signals are deliberately narrow multipliers. They help distinguish reachable and reliable candidates without overpowering technical fit.

### Trap checks protect the top ranks

Trap and honeypot-style checks reduce profiles that look good only through buzzwords, wrong-role AI language, suspicious inconsistencies, or severe availability concerns.

### Reasoning is deterministic and factual

Reasoning is generated from extracted facts and scoring evidence. No hosted LLM is used during ranking or reasoning generation.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Smoke Test

```bash
python generate_submission.py \
  --candidates data/sample_candidates_tiny.json \
  --out outputs/submission_test.csv \
  --top-k 3 \
  --allow-partial \
  --skip-external-validator
```

## Official Reproduce Command

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

This is the canonical command for full challenge reproduction.

## Optional XLSX / Report Command

```bash
python generate_submission.py \
  --candidates ./candidates.jsonl \
  --out ./outputs/submission.csv \
  --xlsx ./outputs/submission.xlsx \
  --report-out ./outputs/submission_run_report.md
```

## Validate Final CSV

```bash
python validate_submission.py outputs/submission.csv
```

Expected output:

```text
Submission is valid.
```

If using the canonical reproduce command, validate `./submission.csv`. If using the optional report command, validate `outputs/submission.csv`.

## Benchmark

```bash
python benchmark_submission.py \
  --candidates candidates.jsonl \
  --mode csv-only \
  --out outputs/benchmark_submission.csv \
  --repeat 2 \
  --compare-determinism
```

Latest local benchmark:

- 100,000 candidates processed.
- CSV-only runtime around 3m16s-3m23s.
- Deterministic repeat passed.

## Final Audit

```bash
python final_hackathon_audit.py \
  --candidates candidates.jsonl \
  --csv outputs/submission.csv \
  --xlsx outputs/submission.xlsx \
  --deck deck/SignalRank_AI_Approach_Deck.pdf \
  --report-out outputs/final_hackathon_audit.md
```

Strict final gate:

```bash
python scripts/final_gate.py \
  --candidates candidates.jsonl \
  --csv outputs/submission.csv \
  --xlsx outputs/submission.xlsx \
  --deck deck/SignalRank_AI_Approach_Deck.pdf
```

## Sandbox Demo

```bash
streamlit run sandbox/app.py
```

The sandbox is a small-sample demo. It accepts JSON/JSONL candidate samples, shows ranked candidates, candidate reasoning, validation status, and demo CSV/XLSX downloads. The full 100K run is CLI-only.

Live sandbox:

https://signalrank-ai-90.streamlit.app/

Deployment settings:

- Main file path: `sandbox/app.py`
- Python: `3.11`
- Secrets: none
- Full dataset is not included or needed for sandbox

## Project Structure

```text
.
├── rank.py
├── generate_submission.py
├── benchmark_submission.py
├── audit_submission.py
├── final_hackathon_audit.py
├── validate_submission.py
├── src/
├── sandbox/
├── docs/
├── deck/
├── tests/
├── scripts/
├── requirements.txt
└── submission_metadata.yaml
```

## Submission Artifacts

| Artifact | Purpose |
|---|---|
| `outputs/submission.csv` | Canonical validated output. |
| `outputs/submission.xlsx` | Portal upload convenience file generated from the same rows. |
| `deck/SignalRank_AI_Approach_Deck.pdf` | Approach deck. |
| `outputs/submission_run_report.md` | Runtime and run summary. |
| `outputs/final_hackathon_audit.md` | Final readiness audit. |
| `sandbox/app.py` | Small-sample demo UI. |

Generated outputs are ignored by git and should be uploaded separately if required.

## Methodology Docs

- `docs/final_methodology.md`
- `docs/architecture_overview.md`
- `docs/judging_notes.md`
- `docs/trap_penalties.md`
- `docs/redrob_behavior_scoring.md`
- `docs/reasoning_strategy.md`
- `docs/final_readiness_criteria.md`
- `docs/repo_review_notes.md`

## Requirements Compliance

| Requirement | Status |
|---|---|
| CPU-only ranking | Satisfied |
| No hosted API calls during ranking | Satisfied |
| Reproducible command | `python rank.py --candidates ./candidates.jsonl --out ./submission.csv` |
| 100-row output | Validated |
| Monotonic scores | Validated |
| Unique ranks and IDs | Validated |
| Reasoning column | Included and non-empty |
| Runtime budget | Under 5 minutes locally |
| Dataset not committed | Protected by `.gitignore` |
| Sandbox/demo | Included as small-sample Streamlit app |

## AI Tools Declaration

AI tools were used for planning, implementation support, debugging, refactoring, and documentation.

The ranking system itself is deterministic local code:

- No hosted LLM calls during ranking.
- No OpenAI, Anthropic, or Gemini API calls.
- No GPU dependency.
- No network access required during ranking.

## Limitations

- No hidden relevance labels were provided.
- Calibration is rule-based and interpreted from the job description.
- The next step would be learning-to-rank with labeled recruiter feedback.
- The system is deterministic and explainable by design.

## Final Upload Checklist

Run before upload:

```bash
pytest
python rank.py --candidates ./candidates.jsonl --out ./outputs/submission.csv
python validate_submission.py outputs/submission.csv
python generate_submission.py --candidates ./candidates.jsonl --out ./outputs/submission.csv --xlsx ./outputs/submission.xlsx --report-out ./outputs/submission_run_report.md --skip-external-validator
python final_hackathon_audit.py --candidates candidates.jsonl --csv outputs/submission.csv --xlsx outputs/submission.xlsx --deck deck/SignalRank_AI_Approach_Deck.pdf --report-out outputs/final_hackathon_audit.md
```

Upload:

- GitHub repository URL.
- `deck/SignalRank_AI_Approach_Deck.pdf`.
- `outputs/submission.xlsx`.

Keep available:

- `outputs/submission.csv`.
- `outputs/submission_run_report.md`.
- `outputs/final_hackathon_audit.md`.

Do not upload:

- `candidates.jsonl`.
- Debug CSV files.
- Sample output files.
- Benchmark output files.
