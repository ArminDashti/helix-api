---
name: Generate analytical report
description: Write a text analysis from fetched warehouse rows at the requested depth
---

# Generate analytical report

## When to use

- `mode=analytical_report`, `analytical_report_chart`, or `auto` when `text_report` is required

## Instructions

1. Base every claim on fetched rows (or a stated empty result). No invented numbers.
2. Depth from `report_type`: `low` = short findings; `medium` = findings plus context; `high` = findings, breakdowns, caveats.
3. Name units, time grain, and filters when they affect the claim. For `analytical_report_chart`, explain the chart that will be shown.
4. Write the report in the run `language`: Persian when `language` is `fa`, English when `en`. Do not translate SQL identifiers.
