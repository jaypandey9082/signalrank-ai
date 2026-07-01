# SignalRank AI Sandbox

This sandbox is a lightweight Streamlit demo for small candidate samples. It lets a reviewer upload JSON/JSONL candidate data, run the deterministic ranker, inspect reasoning, validate the output, and download demo CSV/XLSX files.

It does not run the full 100K candidate file. Use the command-line workflow for official reproduction.

Section 11.5 gives the demo a cleaner reviewer-facing dashboard layout with metric cards, status chips, readable reasoning cards, validation details, and a dedicated downloads tab. If Top K is larger than the loaded sample, the app caps it safely and explains the adjustment.

## Run Locally

```bash
streamlit run sandbox/app.py
```

## Deploy On Streamlit Cloud

1. Push this repo to GitHub.
2. Create a new Streamlit app.
3. Set the main file path to `sandbox/app.py`.
4. Use Python 3.11.
5. Deploy.

## Use The Demo

1. Load the bundled demo sample or upload a small JSON/JSONL sample.
2. Choose Top K.
3. Run the ranking demo.
4. Review ranked rows and reasoning.
5. Download CSV/XLSX if needed.

Do not upload the full `candidates.jsonl` file to the sandbox. The full dataset is not included in the repo and should not be committed.
