# Demo Script

## 60-Second Explanation

SignalRank AI is an explainable candidate discovery engine for the Redrob Senior AI Engineer challenge. It ranks candidates using deterministic evidence from career history, job-description signal mapping, Redrob behavioral signals, and trap checks that reduce keyword-stuffed false positives. It produces a top-100 CSV/XLSX submission with factual reasoning for each candidate. The ranking path is CPU-only, deterministic, and uses no hosted LLM/API calls.

## 3-Minute Demo Flow

1. Open the sandbox.
2. Load the bundled demo sample.
3. Run ranking demo.
4. Show the ranked table.
5. Open the reasoning tab.
6. Show the validation tab.
7. Download CSV/XLSX.
8. Explain that the full run uses `rank.py`.

## Architecture Explanation

Static fit score -> Redrob behavior multiplier -> trap penalty multiplier -> final ranking -> deterministic reasoning.

## Why This Avoids Keyword Traps

The system rewards shipped career evidence more than skill lists. Wrong-role profiles with AI buzzwords are capped or penalized when they lack production retrieval, ranking, evaluation, or product ML evidence.

## If Judges Ask About Runtime

The CSV-only full 100K benchmark completed in about 3m16s-3m23s locally. Ranking uses CPU only and no network/API calls.

## If Judges Ask About AI Tools

AI tools assisted development, refactoring, and documentation. Candidate ranking itself uses deterministic local code and no hosted APIs during execution.
