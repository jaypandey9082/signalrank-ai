# Sandbox Demo

## Purpose

The sandbox is a hosted sanity check for reviewers. It shows that SignalRank AI can load a small candidate sample, run the same deterministic backend used by the CLI, produce ranked rows, explain decisions, validate output, and export demo CSV/XLSX files.

## Why Small Sample Only

The official full ranking is reproduced from the repo with `rank.py`. The hosted sandbox only needs small-sample reproducibility and should stay responsive on lightweight CPU hosting.

## Features

- Upload sample JSON, JSONL, or JSONL.GZ files.
- Run the ranker on up to 100 candidates.
- View ranked results.
- Inspect candidate reasoning.
- Download CSV/XLSX demo outputs.
- Inspect validation results.
- Read the methodology summary.

## Section 11.5 UI Polish

The sandbox now uses a polished Streamlit dashboard layout with a hero section, metric cards, validation chips, readable reasoning cards, and a dedicated downloads tab. Top K is capped safely when a sample has fewer candidates than the selected value, and the demo report records both the selected and effective Top K values.

## UI Checklist

- Bundled demo loads.
- Top-k cap works when the selected value exceeds the sample size.
- Ranking button works.
- Results show.
- Reasoning cards show.
- Validation tab works.
- CSV/XLSX/report downloads work.

## Local Run

```bash
streamlit run sandbox/app.py
```

## Deployment

Deploy with Streamlit Cloud or HuggingFace Spaces as a Streamlit app. The main file path is:

```text
sandbox/app.py
```

## Safety

- The full dataset is not committed.
- The sandbox does not call hosted LLM APIs.
- No API keys are needed.
- No GPU is used.
- Uploaded private data is not cached permanently by the app.
