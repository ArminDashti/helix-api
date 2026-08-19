---
name: generate-analytical-report
description: Write a text analysis from fetched warehouse rows at the requested depth
---

# Generate analytical report

## When to use

- `mode=analytical_report`: full report is the only UI artifact
- `mode=analytical_report_chart` or `auto`: report accompanies chart/grid as required by the output contract

## Instructions

1. Base every claim on fetched rows (or a stated empty result). No invented numbers.
2. Depth from `report_type`: `low` = short findings; `medium` = findings plus context; `high` = findings, breakdowns, caveats. Do not ask for extra years or joins to pad the report.
3. Use plain language; name units, time grain, and filters when they affect the claim.
4. For chart modes, explain what the chart shows. Do not ignore the visual.
5. Write the report in the run `language`: Persian when `language` is `fa`, English when `en`. Do not translate SQL identifiers.
