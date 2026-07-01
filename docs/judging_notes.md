# Judging Notes

## Why Deterministic Scoring Instead Of LLM-Per-Candidate

The challenge needs reproducible ranking over 100K candidates within CPU/runtime limits. Hosted LLM calls would add cost, latency, nondeterminism, and privacy risk. SignalRank AI uses deterministic local scoring and deterministic reasoning.

## Why Career Evidence Is Highest Weight

Skill lists are easy to stuff. Career descriptions provide stronger proof of shipped systems, product ownership, evaluation work, and production constraints.

## Why Behavior Is A Narrow Multiplier

Redrob activity and responsiveness help estimate hireability, but they should not turn a weak technical fit into a top candidate. The behavior score nudges the final ranking without dominating it.

## Why Trap Caps Exist

Caps protect the top ranks from wrong-role profiles, weak AI hype, inconsistent profiles, and keyword-only candidates. They make the ranker more robust against false positives.

## Keyword Stuffers

Wrong-role candidates with AI buzzwords are penalized when they lack career evidence for retrieval, ranking, evaluation, or production ML.

## Strong Plain-Language Candidates

Candidates do not need exact buzzword matches if their career evidence shows production search, ranking, recommendation, evaluation, or related product ML ownership.

## Runtime

Section 10.5 optimized full-data CSV ranking to about 3m16s-3m23s locally, with deterministic repeat output and no network/API calls.

## Improvements With More Time

- Train a learning-to-rank model if labels existed.
- Add local embeddings for better semantic matching.
- Calibrate weights with recruiter feedback.
- Add richer UI workflows.
- Build an A/B testing or offline evaluation framework for future labeled data.
