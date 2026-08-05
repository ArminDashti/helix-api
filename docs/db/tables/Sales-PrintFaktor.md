# Sales.PrintFaktor

## Table overview

Log / parameter row for printing sales invoices in a center. Records which invoice number range was printed, by whom, in which fiscal year/period, and which report template was used.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccMarkazPakhsh | int | YES | | Distribution center id |
| 2 | ShomarehFaktorAz | int | YES | | Invoice number from (range start) |
| 3 | ShomarehFaktorTa | int | YES | | Invoice number to (range end) |
| 4 | ccUser | int | YES | | User who printed |
| 5 | DateEntry | datetime | YES | | Print request datetime |
| 6 | Sal | int | YES | | Year of invoices |
| 7 | ccDorehMaly | int | YES | | Fiscal period id |
| 8 | TypeOfPrinting | smallint | YES | | Print type (original/copy, …) |
| 9 | ReportTypeId | smallint | YES | | Report type id |
| 10 | ReportFileId | smallint | YES | | Report file / template id |
