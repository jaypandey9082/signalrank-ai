# SignalRank AI

Explainable Candidate Discovery Engine

---

# Problem

Recruiting search fails when it ranks keywords instead of real fit.

SignalRank AI is built to separate shipped career evidence from shallow AI buzzwords.

---

# What The JD Really Needs

- Production ranking/search/retrieval
- Recommendation systems
- Embeddings/vector search
- Evaluation frameworks
- Product engineering ownership
- Availability and hiring readiness

---

# System Architecture

```text
Candidate data -> parsing -> features -> static fit
  -> Redrob behavior -> trap penalties -> ranking
  -> deterministic reasoning -> CSV/XLSX
```

---

# Static Fit Scoring

- Career evidence
- Retrieval/ranking evidence
- Skills as support, not proof
- Experience band
- Product-company context
- Location fit
- Evaluation experience

---

# Redrob Behavior Scoring

- Recent activity
- Recruiter response rate
- Notice period
- Relocation/work mode
- Interview reliability
- Profile trust

Behavior is a narrow multiplier, not a replacement for job fit.

---

# Trap And Honeypot-Style Defense

- Wrong-role keyword stuffing
- Weak AI hype without production evidence
- Impossible or inconsistent profile signals
- Non-target AI-only profiles
- Severe low availability

---

# Reasoning

Reasoning is:

- Specific
- Factual
- JD-connected
- Concern-aware
- Deterministic

No hosted LLM calls are used during ranking.

---

# Runtime And Reproducibility

- Full 100K CSV-only run: about 3m16s-3m23s locally
- CPU-only
- No network during ranking
- Deterministic repeat hash
- CSV is canonical

---

# Demo And Submission

- Public GitHub repo
- Streamlit sandbox for small samples
- `submission.csv` for validator
- `submission.xlsx` for portal convenience
- PDF approach deck
