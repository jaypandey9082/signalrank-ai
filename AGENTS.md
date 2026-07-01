# Project Instructions for Future Agents

- Keep code simple, readable, and easy to inspect.
- Do not add hosted API calls for ranking.
- Do not add GPU dependencies.
- Do not commit large candidate datasets.
- Keep ranking deterministic and reproducible.
- Prefer small functions with type hints.
- Every section should include tests or at least a smoke test.
- Do not over-engineer early sections.
- Do not write fake claims in docs or generated reasoning.
- Final output must be reproducible from one command.
- Ranking should stay CPU-only and fit the challenge runtime and memory limits.
- Keep CSV as the canonical submission format; XLSX is a synced portal convenience.
- Do not commit generated packets, benchmark outputs, final CSV/XLSX, or the full candidate dataset.
