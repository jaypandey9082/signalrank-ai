# Methodology Notes

These notes are intentionally rough and practical for the hackathon build.

- The ranker should prioritize career evidence over keyword count.
- Strong evidence should come from actual roles, project descriptions, and relevant systems built.
- Redrob behavioral signals act as modifiers, not the entire score.
- Honeypot-like and keyword-stuffing checks prevent empty buzzword lists from being rewarded.
- Reasoning should explain what the candidate profile actually contains.
- The goal is a fast, explainable ranker that can run on CPU within the challenge limits.
- Early versions should stay easy to inspect before adding more scoring rules.

## Section 2 Notes

- We are validating the data first because later ranking depends on clean features.
- We are not using strict rejection for suspicious records yet.
- Suspicious signals will later feed honeypot or trap penalties.
- The loader stays separate from scoring so data problems are easier to debug.
- Warnings are preserved for inspection, but they do not automatically remove candidates.

## Section 3 Notes

- We converted the JD into explicit signal groups before writing ranking logic.
- This prevents random keyword matching.
- Positive evidence, weak evidence, and negative traps are separated on purpose.
- Full dataset access is not required yet; sample candidates are enough for testing signal matching.
- The full dataset will be required when producing the final top-100 ranking.

## Section 4 Notes

- We now convert each candidate into a structured feature object.
- Evidence snippets are preserved from candidate text so later reasoning can stay factual.
- We are not ranking candidates yet.
- Feature extraction is separated from scoring to keep debugging easy.
- Full data can be inspected with a limit, but final full ranking will come later.

## Section 5 Notes

- We now compute component-level static fit scores.
- The score is intentionally explainable and split into named components.
- Skill-only matches are capped to avoid rewarding keyword stuffing.
- Redrob behavior is not used as a multiplier yet.
- Full honeypot and trap penalties are handled in the Section 7 layer.
- This separation makes the final ranking easier to defend in the interview.

## Section 6 Notes

- Redrob behavior is separated from static job fit.
- The behavior score measures hireability, not technical ability.
- We use a narrow multiplier so platform activity does not overpower career evidence.
- Risk flags are collected now, but final penalties are applied later.
- Full dataset can be inspected with a limit, but final full ranking will come later.

## Section 7 Notes

- Trap penalties are separate from both static fit and Redrob behavior.
- Every trap signal keeps factual evidence so the later reasoning layer can explain the deduction.
- The system never labels a profile as a confirmed honeypot; it only flags honeypot-like profile shapes.
- The additive penalty is capped before it becomes a multiplier.
- Preview rows combine static fit, behavior, and trap penalties for inspection only.
- Final ranking preview is handled in Section 8; final submission export still comes later.

## Section 8 Notes

- We now have a complete ranking preview pipeline.
- The combined score is deterministic and explainable.
- Guardrail caps protect top ranks from weak or risky candidate shapes.
- The preview score is named `final_score_preview` to avoid confusing it with final submission output.
- We still do not generate final challenge submission files.
- Section 9 creates reasoning previews from evidence seeds.

## Section 9 Notes

- We generate reasoning from extracted evidence, not an LLM.
- The reasoning generator is deterministic.
- Each explanation is built from positives, JD terms, and concerns.
- This helps avoid hallucination and makes the ranking easier to defend.
- Reasoning preview output is still separate from final submission export.
- Final CSV/XLSX export is left for Section 10.

## Section 10 Notes

- We now generate challenge-ready submission files.
- CSV and XLSX outputs are synced from the same rows.
- Internal validation catches common format issues before upload.
- Final reasoning is deterministic and based on extracted evidence.
- Full data is required for the final run.
- Sample and partial runs are only for testing.

## Section 10.5 Notes

- Format validation alone is not enough because runtime is a Stage 3 risk.
- We separated CSV-only official reproduction from optional XLSX/report generation.
- The ranking path now keeps only the top-k candidates during full scoring.
- Rich evidence is rebuilt only for selected top rows so reasoning remains factual.
- Deterministic repeat checks catch accidental ordering or output drift.
- Repo and dependency audit checks guard against tracked data, final outputs, network/API packages, and GPU-heavy dependencies.

## Section 11 Notes

- We added a lightweight Streamlit sandbox demo for small samples.
- The UI is intentionally thin and uses the same backend as the CLI.
- The sandbox proves small-sample reproducibility with ranked rows, reasoning, validation, and downloads.
- Full submission generation remains command-line based.
- We avoid uploading or committing the full dataset.

## Section 12 Notes

- We packaged the project for final hackathon upload.
- CSV remains canonical, while XLSX is kept synced for portal convenience.
- Final docs now cover methodology, architecture, judging notes, deployment, and demo flow.
- The approach deck is available as Markdown, offline HTML, and generated PDF.
- Final helper scripts check readiness and prepare a local submission packet without copying the full dataset.

## Section 11.5 Notes

- We polished the sandbox UI without changing ranking or scoring logic.
- The Streamlit demo now uses premium dashboard components for metrics, status, validation, downloads, and reasoning.
- Top K is capped safely when the sample contains fewer candidates than the selected value.
- Demo reports record loaded candidates, processed candidates, selected Top K, effective Top K, runtime, validation summary, and warnings.
