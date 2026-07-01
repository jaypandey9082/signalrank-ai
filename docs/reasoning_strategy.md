# Evidence-Based Reasoning Strategy

## Why reasoning matters

Manual review checks whether explanations are specific, honest, and tied to the Senior AI Engineer JD. Generic praise is not enough, especially because keyword matching is a known trap in this challenge.

## What reasoning can use

- Candidate title.
- Years of experience.
- Career evidence snippets.
- Matched retrieval, ranking, recommendation, embedding, and evaluation terms.
- Redrob availability summary.
- Trap and concern signals.
- Location and logistics facts.

## What reasoning cannot do

- Invent facts.
- Mention hidden labels.
- Claim someone is a confirmed honeypot.
- Rely on hosted LLMs.
- Use generic praise without factual support.
- Mention internal debug terms such as scorecards, guardrails, or preview column names.

## Tone by rank/score

- `elite`: confident and specific, for the strongest preview matches.
- `strong`: positive but still evidence-bound.
- `good`: clear fit with some limits.
- `borderline`: useful but cautious.
- `risky`: lower-confidence language with explicit concerns.

## Concern handling

Concerns are included when supported by the ranked row or scorecard evidence: weak production evidence, wrong-role keyword stuffing, low hireability, weak response signals, high trap risk, non-target AI focus, consulting-only history, or weaker location logistics.

The generator should acknowledge concerns without inventing rejection reasons or turning heuristic risk into confirmed labels.

## Final use

Section 10 will put these reasonings into the final submission file after the final export layer is implemented.
