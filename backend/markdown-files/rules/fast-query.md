---
name: Fast query
---
# Fast query

Warehouse SQL must finish well under the driver statement timeout. Prefer a cheap plan over a complete history scan.

1. Filter the driving table first (`Sales.DarkhastFaktor`): named centers via `ccMarkazPakhsh`, year via `Sal`, dates via `TarikhFaktor` range. Then join lines.
2. Predicates must be sargable: never wrap fact keys or `TarikhFaktor` in functions (no `dbo.CalculatePersianDate(TarikhFaktor)` in WHERE, JOIN, or GROUP BY).
3. If the user did not ask for all years, default to a recent window (`Sal` = current warehouse year, or `TarikhFaktor >= DATEADD(month, -12, GETDATE())`).
4. Always bound the final result with `TOP` / `FETCH`. Rankings (“best seller per center”) = filter → aggregate → `ROW_NUMBER() OVER (PARTITION BY center ORDER BY metric DESC)` → keep `rn = 1`.
5. Join only tables needed for the asked columns. Do not rescan the same unfiltered fact twice.
6. Alias SELECT columns to requested grid names exactly. One grain: one row per asked entity when the prompt is “top of each”.
