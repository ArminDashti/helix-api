---
name: SQL safety
description: Validate SQL as SELECT-only, allowlisted, row-bounded, and cheap enough to finish
---

# SQL safety

## When to use

- Every SQL statement the `sql_fetcher` agent fetches, before execution

## Must reject

- `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `DROP`, `ALTER`, `CREATE`, `EXEC` / `EXECUTE`
- Multi-statement batches that include any write/DDL
- Objects not listed under Allowed objects in `schema/tables.md`
- Unbounded heavy fetches (no TOP/FETCH/LIMIT on the final SELECT; forbidden `SELECT *` when configured; obvious cartesian products)
- Fact-table scans with no `ccMarkazPakhsh` / `Sal` / `TarikhFaktor` predicate when the user named centers, a year, or did not ask for all history
- Scalar functions on fact keys or `TarikhFaktor` in WHERE, JOIN, or GROUP BY (including `dbo.CalculatePersianDate`)
- Nested queries that aggregate the same unfiltered `DarkhastFaktor` / `DarkhastFaktorSatr` more than once

## Must allow (when safe)

- Single `SELECT` (or CTE + SELECT) against allowlisted objects
- Aggregations with clear grouping **after** a sargable filter on the header
- Ranked “top N per group” using `ROW_NUMBER()` then `rn = 1`, with `TOP` on the outer SELECT
- Row-bounded extracts respecting `sql.max_rows`

## Output

Return approve/reject with concrete reasons. Invalid or obviously-too-heavy SQL must not run.
