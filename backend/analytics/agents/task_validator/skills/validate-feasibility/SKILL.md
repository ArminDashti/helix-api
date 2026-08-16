---
name: validate-feasibility
description: Check prompt and mode against Helix product scope and allowlisted schema
---

# Validate feasibility

1. Parse the user ask and mode (`auto`, `chart`, `grid`, `analytical_report`, `analytical_report_chart` and aliases).
2. Map the ask to allowlisted objects in `tables.md` (or conclude none fit).
3. Confirm the ask is warehouse understanding plus report, grid, analysis, or chart — not CRUD, writes, EXEC, or unbounded dumps.
4. Emit `feasible: true|false` with reasons.
