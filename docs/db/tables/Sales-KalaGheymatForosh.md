# Sales.KalaGheymatForosh

## Table overview

Effective selling price list for products (`ccKalaCode`). Each row sets `MablaghForosh` for a date range (`FromDate`–`EndDate`) with approval/status workflow. Used when building sales orders.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccKalaCode | int | NO | | Product code / SKU id |
| 2 | ccKalaGheymatForosh | int | NO | PK, Identity | Price-row primary key |
| 3 | MablaghForosh | float | NO | | Selling price amount |
| 4 | FromDate | datetime | NO | | Price valid-from date |
| 5 | EndDate | datetime | YES | | Price valid-to date (null = open) |
| 6 | CodeVazeiat | tinyint | NO | | Approval/status code |
| 7 | Elat | nvarchar(50) | NO | | Status reason short text |
| 8 | ElatOdat | nvarchar(max) | YES | | Rejection reason detail |
| 9 | FileAddress | nvarchar(256) | YES | | Attached price-change file path |
| 10 | isAutomatic | tinyint | YES | | Auto-generated price flag |
| 11 | CodeVazeiatAutomatic | tinyint | YES | | Status of automatic price flow |
