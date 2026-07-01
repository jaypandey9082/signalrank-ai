# UI Polish Notes

## Goal

Make the sandbox feel like a polished product demo while keeping backend unchanged.

## Design Choices

- Light SaaS dashboard style with white panels, soft slate/blue accents, and system fonts.
- Card-based layout for the hero, metrics, reasoning, validation, and methodology.
- No external assets, remote fonts, analytics, API keys, or heavyweight dependencies.
- Small-sample sandbox only; full ranking remains a command-line workflow.

## What Changed

- Hero section with clear product positioning.
- Metric cards for loaded sample and run summary.
- Result tabs for ranking, reasoning, validation, downloads, and methodology.
- Validation cards and status chips.
- Compact reasoning cards.
- Download buttons for demo CSV, XLSX, and report markdown.
- Top-k cap handling for samples smaller than the selected Top K.

## What Did Not Change

- Ranking algorithm.
- Scoring weights.
- Final submission workflow.
- Command-line full ranking.

## Safety Notes

- No external fonts, tracking scripts, hosted assets, API keys, or heavyweight dependencies.
- Demo reports include loaded count, processed count, selected Top K, effective Top K, validation summary, and warnings.
