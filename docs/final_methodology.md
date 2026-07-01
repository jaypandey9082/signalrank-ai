# Final Methodology

## Problem Interpretation

The challenge is a Senior AI Engineer ranking task, not generic AI keyword matching. The strongest candidates should show production ranking, retrieval, recommendation, search, embeddings, evaluation, and product engineering evidence.

## JD Signal Map

The JD signal map emphasizes ranking/search/retrieval/recommendation systems, embeddings/vector search, evaluation frameworks, production ML ownership, and practical engineering context.

## Candidate Features

SignalRank AI extracts structured signals from profile fields, career history, skills, education, and Redrob platform signals. Career descriptions are treated as stronger evidence than skill lists because they better show what a candidate actually shipped.

## Static Fit Score

Static fit combines career evidence, retrieval/ranking evidence, skill support, experience band, product-company context, location fit, evaluation experience, and education relevance. The components are explicit and inspectable.

## Redrob Behavior Multiplier

Redrob behavior measures hireability/readiness: activity, response rate, notice period, relocation/work mode, market interest, process reliability, profile trust, and technical activity. It is a narrow multiplier so platform activity does not overpower technical fit.

## Trap Penalty Multiplier

Trap checks reduce false positives from wrong-role keyword stuffing, weak AI hype without production evidence, profile inconsistencies, low availability risk, consulting-only histories without product evidence, and non-target AI-only profiles.

## Guardrail Caps

Guardrail caps prevent profiles with severe trap risks or no real retrieval/ranking evidence from drifting into top ranks purely through keyword matches.

## Reasoning

Reasoning is deterministic and evidence-based. It uses extracted candidate facts and scorecards, not hosted LLM calls. Explanations are short, factual, JD-connected, and concern-aware.

## Runtime

After Section 10.5 optimization, CSV-only full-data ranking ran under the 5-minute target locally, with measured runs around 3m16s-3m23s for 100K candidates.

## Limitations

- No hidden ground truth labels were available.
- The design is rule-based, not trained on labels.
- Weights are tuned by JD interpretation and sample inspection.
- With more time, recruiter feedback and labeled outcomes could improve calibration.
