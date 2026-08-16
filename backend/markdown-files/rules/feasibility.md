---
name: Feasibility
---
# Task Validator rules

1. Reject tasks that require tables/views outside `tables.md`.
2. Reject tasks that need writes, admin access, EXEC, or package installation.
3. Accept only modes `auto`, `chart`, `grid`, `analytical_report`, `analytical_report_chart` (aliases `analysis`, `research`, `both`).
4. Reject work that is not warehouse understanding plus report, grid, analysis, or chart.
5. If infeasible, explain why in plain language — do not invent a workaround that violates security or product scope.
