# Data Inspection

Data inspection matters in this challenge because the final ranker will depend on profile, career, skill, education, and Redrob activity fields being present and usable. If those fields are missing or oddly shaped, scoring rules can become noisy or unfair.

The inspector currently checks:

- Candidate ID format, such as `CAND_0000001`.
- Required top-level fields like `profile`, `career_history`, `education`, `skills`, and `redrob_signals`.
- Required profile fields such as headline, summary, location, current title, and years of experience.
- Career history shape and required role fields.
- Skill names, proficiency values, endorsements, and suspicious expert skills with zero duration.
- Redrob signal coverage, including response rates, notice period, salary range, and verification flags.
- Dataset-level summaries for common titles, locations, countries, industries, skills, and experience bands.

Warnings do not automatically remove candidates. Some warnings are suspicious but not enough to reject a profile on their own. For example, salary minimum greater than maximum may be a typo, and `last_active_date` earlier than `signup_date` may be dirty platform data. Later ranking sections can decide whether those signals should reduce confidence or trigger honeypot/trap penalties.

Examples the validator can catch:

- Wrong candidate ID format.
- Missing profile fields.
- Salary minimum greater than salary maximum.
- `last_active_date` earlier than `signup_date`.
- Expert skill with zero recorded duration.

Later sections add feature extraction, scoring, trap detection, final reasoning, and CSV/XLSX exports.
