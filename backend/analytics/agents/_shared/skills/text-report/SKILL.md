---
name: text-report
description: Produce a clear textual analysis for analytical_report modes (see generate-analytical-report)
---

# Text report

## When to use

- `mode=analytical_report`: full report is the only UI artifact
- `mode=analytical_report_chart` or `auto`: report accompanies chart/grid as required by the output contract

## Instructions

1. Follow `generate-analytical-report` for depth (`report_type`) and sourcing.
2. Use plain language; include units, time grain, and caveats when relevant.
3. For chart modes, explain what the chart shows — do not ignore the visual.
4. Do not invent numbers that were not computed from the fetch.
