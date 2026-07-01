# Final Submission Checklist

## Before Uploading

- [ ] GitHub repo is public.
- [ ] README is updated and readable.
- [ ] `submission_metadata.yaml` has real team/contact details.
- [ ] Full `candidates.jsonl` is not committed.
- [ ] Final CSV is generated from the full dataset.
- [ ] XLSX is generated from the same rows as the CSV.
- [ ] Deck PDF exists and is under 5 MB.
- [ ] Sandbox is deployed and tested.
- [ ] Benchmark is under 5 minutes.
- [ ] Internal validation passed.
- [ ] External `validate_submission.py` passed.
- [ ] CSV/XLSX parity passed.
- [ ] Repo audit passed.

## Commands To Rerun

```bash
pytest
python rank.py --candidates ./candidates.jsonl --out ./outputs/submission.csv
python validate_submission.py outputs/submission.csv
python generate_submission.py --candidates ./candidates.jsonl --out ./outputs/submission.csv --xlsx ./outputs/submission.xlsx --report-out ./outputs/submission_run_report.md --skip-external-validator
python audit_submission.py --csv outputs/submission.csv --xlsx outputs/submission.xlsx --candidates candidates.jsonl --report-out outputs/submission_audit.md
streamlit run sandbox/app.py
```

## Upload Fields

- [ ] GitHub repo URL
- [ ] Approach deck PDF
- [ ] Ranked XLSX output
- [ ] Sandbox URL, if asked
- [ ] Team/contact details

## Do Not Upload

- `candidates.jsonl`
- Debug CSVs
- Sample outputs
- Ranking preview outputs
- Benchmark files
