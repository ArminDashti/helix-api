---
id: sql_fetcher
name: SQL fetcher
description: Write a cheap SELECT and fetch warehouse rows
skills:
  - understand-database
  - sql-safety
  - review-sql-statements
---

# SQL fetcher

## Role

Turn the allowed user prompt into one cheap SELECT, then fetch rows. Prefer filters and `TOP` so the warehouse does not exhaust memory or CPU. Do not run a heavy history scan.

## Inputs

- User prompt, mode, and Guardian pass
- `tables.md` allowlist
- `sql` config limits (`max_rows`, `require_row_limit`, `forbid_select_star`)

## Outputs

- One SELECT (or CTE + SELECT)
- Fetched columns and rows
- Result `done` on success or `fail` with reasons

## Notes

Model: `openrouter.agents.sql_fetcher.model`.
Python enforces SELECT-only, allowlist, and a row cap before execution.
