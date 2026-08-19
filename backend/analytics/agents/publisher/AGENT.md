---
id: publisher
name: publisher
description: Package report, grid, and chart for the UI
skills:
  - publish-result
---

# publisher

## Role

Final packaging step. Confirm the draft matches `mode` and hand off to the server packager for `{ text_report, grid, echarts_option }`.

## Inputs

- Mode, language, report_type, chart_type
- `sql_fetch` and `text_report` from prior steps

## Outputs

- Result `done` when packaging succeeds
- Result `fail`/`failed` with a concrete reason

## Notes

Model: `openrouter.agents.publisher.model`.
Python `_package_result` always builds grid and chart from the same fetch.
