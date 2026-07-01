# Feature Extraction

## Why we extract features first

Ranking needs structured evidence, not just raw text. The Senior AI Engineer role depends on real production experience with ranking, retrieval, search, recommendations, embeddings, evaluation, and product engineering. Feature extraction turns candidate profiles into inspectable facts before any scoring is applied.

## Main feature groups

- Profile, title, location, and experience fields.
- Skills, proficiency, endorsements, durations, and assessment scores.
- Career evidence from titles, companies, industries, and descriptions.
- Product versus service company context.
- Redrob raw signals such as availability, response rate, notice period, relocation, GitHub, and verification.
- Diagnostic flags for suspicious or useful patterns.

## Career evidence

Career descriptions matter more than skill keywords. A candidate who says they owned production search relevance or recommendation pipelines has stronger evidence than someone who lists many AI tools with no matching work history.

The extractor keeps short snippets from candidate text so later reasoning can quote factual profile evidence instead of inventing explanations.

## Diagnostic flags

Diagnostic flags are not final penalties yet. They mark patterns that scoring can use later, such as wrong-role titles, invalid salary ranges, platform date inconsistencies, keyword-stuffing shape, real retrieval/ranking evidence, evaluation evidence, production evidence, and likely non-target AI-only profiles.

## What comes next

Section 5 will convert these extracted features into feature-level scores. Final ranking and submission export will come later.
