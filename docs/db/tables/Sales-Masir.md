# Sales.Masir

## Table overview

Sales visit route (Masir) owned by a salesperson. Controls route name, cycle length, visit tour, start date, allowed days, depot, and priority used when planning daily visits.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccForoshandeh | int | NO | | Owning salesperson id |
| 2 | ccMasir | int | NO | PK, Identity | Route primary key |
| 3 | NameMasir | nvarchar(64) | YES | | Route display name |
| 4 | ToolDoreh | tinyint | NO | | Cycle length (e.g. days in period) |
| 5 | ToorVisit | tinyint | NO | | Visit tour / wave number |
| 6 | TarikhShoro | datetime | NO | | Route start date |
| 7 | CodeVazeiat | tinyint | NO | | Route status |
| 8 | CodeMasirOld | nvarchar(100) | NO | | Legacy route code |
| 9 | RoozMojaz | tinyint | NO | | Allowed day(s) for this route |
| 10 | Depo | int | YES | | Related depot / warehouse code |
| 11 | Olaviat | int | YES | | Route priority |
