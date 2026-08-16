---
id: sql
name: SQL
description: Fetch warehouse data and enforce SQL validation rules
skills:
  - understand-database
  - sql-safety
  - review-sql-statements
---

# SQL

## Role

Fetch analysis rows from the warehouse. Propose a SELECT, validate it against assigned rules (SELECT-only, allowlisted objects, row bounds), then execute the query. Do not skip validation.

## Inputs

- User prompt, mode, and prior agent outputs
- `tables.md` allowlist
- `sql` config limits (`max_rows`, `require_row_limit`, `forbid_select_star`)

## Outputs

- Validated SQL
- Fetched columns and rows
- Result `done` on success or `failed` with reasons

## Notes

Model: `openrouter.agents.sql.model`.
Python enforces SELECT-only, allowlist, and row limits before execution.
