# Technical Architect rules

1. Specify only allowlisted objects from `tables.md`.
2. Require SELECT-only, row-bounded SQL in the plan.
3. Define exact artifacts for the mode (`text_report` / `echarts_option`).
4. Do not write full production code here — blueprint only; Code Builder implements.
