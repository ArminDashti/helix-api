---
name: echarts-response
description: Produce a valid Apache ECharts option JSON object for chart or both modes
---

# ECharts response

## When to use

- `mode=chart` or `mode=both`

## Instructions

1. Emit a single ECharts `option` object (title, axes/series or equivalent for the chart type).
2. Prefer readable labels, legends, and units where applicable.
3. Data in the option must come from allowlisted queries / sandbox results — no fabricated series.
4. Output must be JSON-serializable for the frontend (`echarts-for-react`).
