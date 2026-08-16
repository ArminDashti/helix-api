---
name: write-technical-blueprint
description: Produce an implementation blueprint for Code Builder and the auditor
---

# Write technical blueprint

1. List data sources (allowlisted) and required columns.
2. Describe transforms / ML steps at a technical level.
3. Specify SQL constraints (SELECT, TOP/FETCH, no SELECT * if forbidden).
4. Specify output artifacts per mode: `text_report`, `grid`, and/or `echarts_option` (`chart_type` when a chart is needed).
