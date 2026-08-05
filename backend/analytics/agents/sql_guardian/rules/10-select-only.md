# SQL Guardian rules

1. Allow only SELECT (and safe CTE+SELECT); reject INSERT/UPDATE/DELETE/MERGE/DDL/EXEC and write batches.
2. Every referenced object must appear in `tables.md` Allowed objects.
3. Reject heavy fetches: missing row bounds when returning raw rows; forbidden SELECT *; detectable cartesian products.
4. Respect `sql_guardian.max_rows`, `require_row_limit`, and `forbid_select_star` from config.
5. On reject, list concrete fixes for Code Builder (capped by `sql_guardian.max_retries`).
