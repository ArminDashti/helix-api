---
name: generate-grid
description: Build a tabular grid from fetched SELECT rows
---

# Generate grid

## When to use

- `mode=grid`, `analytical_report_chart`, or `auto` when a table of rows is required

## Instructions

1. Use only columns and rows from the SQL fetch.
2. Emit `{ "columns": [...], "rows": [...] }`. Honor requested `columns` when provided and present in the fetch.
3. Do not pad missing cells with invented values. Empty fetch → no grid.
