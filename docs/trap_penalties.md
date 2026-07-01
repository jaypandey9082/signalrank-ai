# Trap Penalties

Section 7 adds a deterministic trap and honeypot-like penalty layer. It does not produce the final ranking or submission file.

The penalty engine looks for suspicious profile shapes that can inflate a candidate if the ranker only counts AI keywords:

- Wrong-role titles with AI keyword stuffing.
- Weak AI hype without production retrieval, ranking, or evaluation evidence.
- Consulting-only or service-only histories with no product ML ownership.
- Non-target AI specialties without NLP, retrieval, ranking, embedding, or evaluation evidence.
- Expert skills with zero or tiny recorded duration.
- Profile and platform data inconsistencies.
- Severe low-availability patterns.
- Combined honeypot-like profile shapes.

Each signal carries a factual evidence list from candidate data. The system does not call any candidate a confirmed honeypot. The combined signal is named `honeypot_like_profile_shape` and is only a heuristic risk flag.

The total additive penalty is capped at `0.65`. The capped value maps to a multiplier:

- `clean`: `1.00`
- `minor_risk`: `0.97`
- `moderate_risk`: `0.90`
- `high_risk`: `0.75`
- `extreme_risk`: `0.50`

Preview mode applies static fit, then the Redrob behavior multiplier, then the trap multiplier. This preview is for debugging only and is not the final ranking score.

Useful commands:

```bash
python inspect_traps.py --candidates data/sample_candidates_tiny.json
python inspect_traps.py --candidates data/sample_candidates.json --top 25
python inspect_traps.py --candidates candidates.jsonl --limit 1000 --top 25 --report-out outputs/trap_report_1k.md
python inspect_traps.py --candidates candidates.jsonl --limit 1000 --include-preview
```
