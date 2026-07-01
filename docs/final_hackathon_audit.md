# Final Hackathon Audit

Section 12.5 adds an additive audit layer for final submission readiness. It does not change ranking, scoring, reasoning, or final output generation.

## Full Audit

```bash
python final_hackathon_audit.py \
  --candidates candidates.jsonl \
  --csv outputs/submission.csv \
  --xlsx outputs/submission.xlsx \
  --deck deck/SignalRank_AI_Approach_Deck.pdf \
  --report-out outputs/final_hackathon_audit.md
```

External full-data path example:

```bash
python final_hackathon_audit.py \
  --candidates "/path/to/challenge/candidates.jsonl" \
  --csv outputs/submission.csv \
  --xlsx outputs/submission.xlsx \
  --deck deck/SignalRank_AI_Approach_Deck.pdf \
  --report-out outputs/final_hackathon_audit.md
```

## Strict Final Gate

```bash
python scripts/final_gate.py \
  --candidates candidates.jsonl \
  --csv outputs/submission.csv \
  --xlsx outputs/submission.xlsx \
  --deck deck/SignalRank_AI_Approach_Deck.pdf
```

The final gate exits non-zero when upload blockers remain.

## Portal Packet Check

```bash
python scripts/check_portal_packet.py \
  --github-url TODO \
  --sandbox-url TODO \
  --deck deck/SignalRank_AI_Approach_Deck.pdf \
  --xlsx outputs/submission.xlsx \
  --csv outputs/submission.csv
```

Placeholder URLs are expected blockers until real public links are available.

## Reports

- `outputs/final_hackathon_audit.md`
- `outputs/final_gate_report.md`
- `outputs/final_portal_packet_report.md`
- `outputs/final_submission_quality_report.md`

Generated reports are local artifacts and should not be committed unless explicitly requested.
