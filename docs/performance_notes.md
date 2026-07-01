# Performance Notes

## Before runtime

- Section 10 full CSV/XLSX/report run: 10m 53.6s

## After runtime

- Section 10.5 CSV-only benchmark run 1: 3m 16.3s.
- Section 10.5 CSV-only benchmark run 2: 3m 22.6s.
- CSV-only deterministic repeat check passed with identical SHA-256 output.
- Optional CSV/XLSX/report run: 3m 24.2s.

## Bottlenecks found

- The previous ranking preview path scored every candidate, materialized every ranked row, then sorted all rows to keep only the top 100.
- Feature extraction built career text more than once per candidate.
- The scoring pass collected rich evidence snippets and matched signal maps for every candidate, even though final reasoning only needs rich evidence for the selected top 100.
- `rank.py` inherited the richer Section 10 exporter defaults, so a simple final command could also create a report and run the external validator.

## Optimizations applied

- `rank.py --out` is now a CSV-only official path unless XLSX/report/validator flags are explicitly provided.
- Full ranking streams candidates and keeps only the top-k rows with a deterministic heap.
- The all-candidate scoring pass skips expensive evidence snippets and unused matched-signal maps.
- Top-k rows are re-enriched after selection so final reasoning remains factual.
- Stage timings, deterministic repeat checks, CSV/XLSX parity checks, and repo audit tooling were added.

## Remaining risks

- If the measured CSV-only full run still exceeds 5 minutes, the next optimization target is lower-level term matching and Redrob date parsing.
- The CSV is canonical; XLSX and markdown reports are review artifacts and should not be included in the official runtime unless required by the portal.
