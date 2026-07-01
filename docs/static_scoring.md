# Static Scoring

## What this section does

Section 5 converts extracted candidate features into component-level fit scores. The goal is to make the candidate-job match explainable before later behavior modifiers and trap penalties.

## What this section does not do

This section does not create the final ranking, does not generate `submission.csv`, does not apply the Redrob availability multiplier, and does not run the honeypot/trap penalty engine.

## Component scores

- `career_evidence`: rewards career-history proof of shipped ranking, retrieval, search, recommendation, and product ML work.
- `retrieval_ranking`: rewards search, matching, recommendation, embeddings, vector/hybrid retrieval, and ranking terms, with career text weighted more than skills.
- `skills`: rewards relevant skills, assessment evidence, and advanced/expert proficiency, while capping skill-only matches.
- `experience_fit`: rewards the JD's rough 5-9 year target, especially 6-8 years.
- `product_company`: rewards product-company or product-industry context.
- `location_fit`: supports Pune/Noida and other acceptable India locations.
- `evaluation_experience`: rewards NDCG, MRR, MAP, A/B testing, relevance labels, and offline/online evaluation evidence.
- `education_signal`: gives small support for CS, ML, AI, data science, IT, statistics, and mathematics education.

## Why career evidence is weighted highest

The JD values shipped production systems more than keyword skills. A candidate who has actually owned a ranking or recommendation system should beat a candidate with many AI tool names but no matching work history.

## Why skills are capped

The dataset contains keyword-stuffed profiles. Skill lists are useful, but a profile with LangChain, Pinecone, prompt engineering, and embeddings should not score near-perfect if the career history is marketing, HR, content, or operations work.

## Debug usage

Use `inspect_scores.py` to inspect static score behavior:

```bash
python inspect_scores.py --candidates data/sample_candidates.json --top 20
python inspect_scores.py --candidates candidates.jsonl --limit 1000 --top 25 --report-out outputs/static_score_report_1k.md
```

The debug CSV from `--debug-csv` is not a submission file. It is only for understanding component scores.

## Next steps

Section 6 adds Redrob behavior scoring. Section 7 adds trap and honeypot-like penalties. Section 8 combines the pieces into a ranking preview. Section 9 adds reasoning previews, and final submission export comes later.
