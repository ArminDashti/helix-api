# data-gatherer warehouse SQL rules

Warehouse SQL must finish well under the driver statement timeout. Prefer a cheap plan over a complete history scan.

1. Allow only SELECT (and safe CTE+SELECT); reject INSERT/UPDATE/DELETE/MERGE/DDL/EXEC and write batches.
2. Every referenced object must appear in assigned references or the live catalog.
3. Filter the driving table first with sargable predicates on keys the user named (center, year, date range). Then join detail tables.
4. Predicates must be sargable: do not wrap filter keys or date columns in functions in WHERE, JOIN, or GROUP BY.
5. Iranian months/years: `Sal` is Jalali; `TarikhFaktor` is Gregorian. Filter `Sal = 1405` plus a Gregorian `TarikhFaktor` range. Never `YEAR(TarikhFaktor) = 1405` and never `'1405-04-01'` date literals.
6. If the user did not ask for all years, default to a recent window (current year or last 12 months per references).
7. Always bound the final result with `TOP` / `FETCH` / `LIMIT`. Reject missing row bounds, forbidden `SELECT *`, cartesian products, and unfiltered fact scans.
8. Rankings: filter, aggregate, window rank, keep top row per group. Alias SELECT columns to requested grid names exactly.
9. Join only tables needed for the asked columns. Do not rescan the same unfiltered fact twice.
10. Resolve center names on `Global.MarkazPakhsh` (exact name) then filter `ccMarkazPakhsh` on the header.
11. Respect `sql.max_rows`, `require_row_limit`, and `forbid_select_star` from config.
12. On reject or warehouse error, return `fail`/`failed` with concrete fixes. Rewrite until success or retry cap.
