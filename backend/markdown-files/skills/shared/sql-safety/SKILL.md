---
name: SQL safety
description: Validate SQL as SELECT-only, allowlisted, and not an unbounded heavy fetch
---

# SQL safety

## When to use

- Every SQL statement the `sql` agent fetches, before execution

## Must reject

- `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `DROP`, `ALTER`, `CREATE`, `EXEC` / `EXECUTE`
- Multi-statement batches that include any write/DDL
- Objects not listed under Allowed objects in `schema/tables.md`
- Unbounded heavy fetches (no TOP/FETCH/LIMIT when returning raw rows; forbidden `SELECT *` when configured; obvious cartesian products)

## Must allow (when safe)

- Single `SELECT` (or CTE + SELECT) against allowlisted objects
- Aggregations with clear grouping
- Row-bounded extracts respecting `sql.max_rows` / `sandbox.max_rows`

## Output

Return approve/reject with concrete reasons. Invalid SQL must not run.
