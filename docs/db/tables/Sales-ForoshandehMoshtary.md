# Sales.ForoshandehMoshtary

## Table overview

Assignment of customers to salespeople and visit routes. Defines which Moshtary belongs to which Foroshandeh/Masir, visit day (`RoozVizit`), priority, and credit/block reasons for that assignment.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccForoshandeh | int | NO | | Salesperson id |
| 2 | ccMoshtary | int | NO | | Customer id |
| 3 | ccMasir | int | NO | | Route (Masir) id |
| 4 | ccForoshandehMoshtary | int | NO | PK, Identity | Assignment primary key |
| 5 | RoozVizit | tinyint | NO | | Visit day of week/cycle |
| 6 | Olaviat | int | NO | | Visit priority / sequence |
| 7 | CodeVazeiat | tinyint | NO | | Assignment status |
| 8 | ElatGheirFaalMoshtary | nvarchar(200) | NO | | Reason customer inactive on this link |
| 9 | BlockedByEtebar | tinyint | NO | | Blocked due to credit flag |
| 10 | ElatBlockedByEtebar | nvarchar(200) | NO | | Credit-block reason text |
