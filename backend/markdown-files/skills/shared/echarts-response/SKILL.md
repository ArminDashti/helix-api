---
name: ECharts response
description: Produce a valid Apache ECharts option JSON object from fetched rows
---

# ECharts response

## When to use

- `mode=chart`, `analytical_report_chart`, or `auto` when a chart is required

## Instructions

1. Emit a single ECharts `option` object (title, axes/series or equivalent).
2. Use `chart_type`: `bar`, `line`, `area`, `pie`, `donut`, `scatter`, `stacked_bar`, `horizontal_bar`.
3. Series values must come from the SQL fetch — no fabricated series.
4. Output must be JSON-serializable for the frontend (`echarts-for-react`).
