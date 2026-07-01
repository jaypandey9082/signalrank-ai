# Scoring Strategy Draft

Section 3 only defines the draft configuration. It does not apply scores to candidates yet.

## Draft Formula

The first scoring pass will likely combine normalized feature scores with these draft weights:

- career_evidence: 0.22
- retrieval_ranking: 0.18
- skills: 0.13
- experience_fit: 0.10
- product_company: 0.10
- redrob_availability: 0.10
- location_logistics: 0.07
- evaluation_experience: 0.05
- education_signal: 0.03
- verification_github: 0.02

Career evidence gets the highest weight because the JD is asking for someone who has actually built and shipped relevant systems. A candidate with plain wording but real ranking or search ownership should beat a keyword-heavy profile with no matching career path.

Retrieval and ranking get high weight because they are the core of the role: search relevance, recommendations, candidate matching, vector retrieval, reranking, and evaluation.

Redrob availability is a modifier, not the whole score. Open-to-work status, response rate, notice period, and verification can help prioritize reachable candidates, but they should not override role fit.

## Penalties

Penalties exist because the challenge is likely to include traps: wrong-role keyword stuffing, weak AI hype without production work, service-company-only histories with no product evidence, inactive candidates, invalid salary ranges, date inconsistencies, and expert skills with zero duration.

These penalties should reduce confidence later, but they should be explainable and tied to profile data.

## Tuning

All weights are draft. They should be revisited after feature extraction exists and after we inspect behavior on the larger dataset.
