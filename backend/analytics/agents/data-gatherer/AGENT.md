---
id: data-gatherer
name: data-gatherer
description: Write a cheap SELECT from catalog and references, then fetch rows
skills:
  - understand-database
  - gather-data
---

# data-gatherer

## Role

Turn the allowed user prompt into one cheap SELECT using all references and the live catalog, then fetch rows. On warehouse error, rewrite and retry until success or the retry cap.

## Inputs

- User prompt, mode, and guardian pass
- All assigned references and live catalog
- `sql` config limits (`max_rows`, `require_row_limit`, `forbid_select_star`)

## Outputs

- One SELECT (or CTE + SELECT)
- Fetched columns and rows
- Result `done` on success or `fail`/`failed` with reasons

## Notes

Model: `openrouter.agents.data-gatherer.model`.
Python enforces SELECT-only, allowlist, and a row cap before execution.
The server injects Jalali→Gregorian date bounds into the data-gatherer prompt when the user names an Iranian month/year.
