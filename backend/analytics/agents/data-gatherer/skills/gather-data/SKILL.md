---
name: gather-data
description: Write SELECT from references and catalog, validate safety, execute, and retry on errors
---

# Gather data

1. Read the user prompt, mode, all references, and the live catalog.
2. Write one cheap SELECT with a row bound on the final SELECT. For Iranian months, filter `Sal` plus a Gregorian `TarikhFaktor` range from the run-context calendar hint.
3. Return JSON with `sql`, `result`, and `message`.

## SQL safety (before execution)

**Must reject**

- `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `DROP`, `ALTER`, `CREATE`, `EXEC` / `EXECUTE`
- Multi-statement batches that include any write/DDL
- Objects not listed in references or the live catalog
- Unbounded heavy fetches (no TOP/FETCH/LIMIT on the final SELECT; forbidden `SELECT *` when configured; obvious cartesian products)
- Full fact-table scans with no filter when the user named centers, a year, or did not ask for all history
- Scalar functions on filter keys or date columns in WHERE, JOIN, or GROUP BY
- Nested queries that aggregate the same unfiltered fact more than once

**Must allow (when safe)**

- Single `SELECT` (or CTE + SELECT) against catalog-listed objects
- Aggregations with clear grouping **after** a sargable filter on the driving table
- Ranked "top N per group" using a window function then keep rank = 1, with `TOP` on the outer SELECT
- Row-bounded extracts respecting `sql.max_rows`

## Retry behavior

4. On warehouse error in context, fix the SQL using the error text; do not invent numbers.
5. When `last_error` contains validator gaps from the first validator visit, revise SQL to fix those specific mismatches (table, filters, grain, metrics). Do not weaken row bounds or SELECT-only rules.
6. On approve, the server executes the SQL and stores rows in `sql_fetch`.
