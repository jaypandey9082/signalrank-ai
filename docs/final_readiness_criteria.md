# Final Readiness Criteria

## Hard Blockers

- CSV is invalid.
- CSV has fewer or more than 100 rows.
- External validator fails when available.
- Official reproduce command runtime is over 5 minutes.
- Reproduced output is nondeterministic.
- CSV and XLSX mismatch.
- `candidates.jsonl` or `candidates.jsonl.gz` is tracked in git.
- Generated final submission outputs are tracked in git.
- Deck PDF is missing for portal upload.
- `submission_metadata.yaml` still has placeholders.
- Public GitHub URL is missing.
- Sandbox/demo link is missing if the portal requires it.

## Warnings

- Reasoning is slightly long but still valid.
- PDF deck is not generated, but HTML deck exists for manual export.
- Sandbox is not deployed yet.
- Top-100 review needs manual inspection.
- Team/contact placeholders are intentionally left until final upload.
- External validator is unavailable in the repo root but may exist in the hackathon bundle.

## Winning-Quality Signals

- Top 10 candidates show real retrieval, ranking, search, recommendation, evaluation, or production ML evidence.
- Zero obvious wrong-role candidates appear in the top 10.
- Top 100 has low trap-risk concentration.
- Reasoning is factual, varied, and connected to the Senior AI Engineer JD.
- Official reproduction is deterministic and under 5 minutes on CPU.
- Public repo is clean and does not include private/full candidate data.
- Sandbox and deck are polished enough for judge review.
