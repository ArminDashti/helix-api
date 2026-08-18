---
name: Select only
---
# SQL fetcher rules

1. Allow only SELECT (and safe CTE+SELECT); reject INSERT/UPDATE/DELETE/MERGE/DDL/EXEC and write batches.
2. Every referenced object must appear in `tables.md` Allowed objects.
3. Reject heavy fetches: missing `TOP`/`FETCH`/`LIMIT` on the final SELECT; forbidden SELECT *; cartesian products; unfiltered `DarkhastFaktor`/`DarkhastFaktorSatr` scans; functions on `TarikhFaktor` or join keys.
4. Filter header first (`ccMarkazPakhsh`, `Sal`, `TarikhFaktor` range), then join lines. Default to a recent `Sal` or last 12 months unless the user asked for all history.
5. Keep the result small: alias only asked columns; always bound with `TOP`. Rankings: `ROW_NUMBER()` per group, keep `rn = 1`.
6. Respect `sql.max_rows`, `require_row_limit`, and `forbid_select_star` from config. Prefer a few hundred rows, not thousands.
7. On reject, return result `fail` with concrete fixes. Do not execute invalid SQL.
