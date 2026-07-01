# Redrob Behavior Scoring

## What this section does

Section 6 scores candidate availability, responsiveness, and hireability from Redrob platform signals. The output is a Redrob availability score, a behavior band, a narrow multiplier, and risk flags for inspection.

## Why behavior matters

A technically strong candidate who has not logged in recently or rarely responds to recruiters may not be reachable. Behavior signals help estimate whether a candidate can realistically move through a hiring process.

## Component scores

- `activity_recency`: recent platform activity from `last_active_date`.
- `availability_intent`: open-to-work status, recent applications, work-mode preference, and relocation willingness.
- `recruiter_responsiveness`: recruiter response rate and response speed.
- `notice_logistics`: notice period, relocation willingness, and hybrid/flexible logistics.
- `market_interest`: recruiter views, search appearances, and saved-by-recruiter activity.
- `process_reliability`: interview completion and offer acceptance behavior.
- `profile_trust`: profile completeness, verification, assessments, connections, and endorsements.
- `technical_activity`: GitHub activity and skill assessment scores.

## Behavior multiplier

The multiplier is intentionally narrow. Strong candidates can be boosted slightly, and risky candidates can be down-weighted. Behavior alone cannot make a wrong-profile candidate top-ranked.

## Risk flags

Risk flags are warnings, not final rejection rules. They include inactivity, low recruiter response, slow response, high notice period, not open to work, not willing to relocate, unverified profiles, platform date inconsistency, and invalid salary range.

## What comes next

Section 7 adds trap and honeypot-like penalties. Section 8 combines static fit, Redrob behavior, and penalties into a ranking preview.
