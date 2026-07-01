# Architecture Draft

SignalRank AI will use a simple batch pipeline:

```text
Input -> Data Loader -> Normalization -> Feature Extraction -> Scoring -> Reasoning -> Export
```

## Sections

- Input: candidate data from the challenge file, expected to be large and compressed.
- Data Loader: local JSON, JSONL, and JSONL.GZ reading with streaming support.
- Normalization: clean text fields and join useful profile evidence.
- Feature Extraction: derive role-fit signals from career history, skills, education, and Redrob fields.
- Scoring: deterministic CPU-only ranking for the Senior AI Engineer target role.
- Reasoning: short factual explanations tied to candidate data.
- Export: CSV first, with XLSX support added after the scoring output is stable.

Current sections cover loading, inspection, feature extraction, static scoring, Redrob behavior scoring, and trap detection. Later sections will add final ranking, reasoning export, and any demo surface.
