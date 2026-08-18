---
name: Output contract
---
# Output contract

Honor request `mode` when planning or packaging. Aliases: `analysis` / `research` → `analytical_report`; `both` → `analytical_report_chart`.

| Mode | `text_report` | `grid` | `echarts_option` |
|------|---------------|--------|------------------|
| `analytical_report` | required | null | null |
| `grid` | null | required | null |
| `chart` | null | null | required |
| `analytical_report_chart` | required | optional | required |
| `auto` | required | optional | optional |

- `report_type`: `low` | `medium` | `high` (aliases `simple` → low, `summary` → medium, `deep` → high). Depth of `text_report` only.
- `chart_type`: `bar` | `line` | `area` | `pie` | `donut` | `scatter` | `stacked_bar` | `horizontal_bar`.
- Unused artifacts must be null. Do not invent numbers. Payload must be JSON-serializable.
- Grid: few rows (one per asked entity for rankings). SELECT aliases must match requested column names.
