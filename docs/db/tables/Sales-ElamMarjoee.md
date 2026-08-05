# Sales.ElamMarjoee

## Table overview

Customer return declaration header (Elam Marjoee). Records a return request from a customer via a salesperson/center, optionally linked to original `DarkhastFaktor`, with status and reason. Line details live in `ElamMarjoeeSatr`.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccElamMarjoee | bigint | NO | PK, Identity | Return declaration primary key |
| 2 | ccElamMarjoeePPC | nvarchar(20) | NO | | PPC/tablet external id |
| 3 | CodeNoeVorod | tinyint | NO | | Entry channel/type |
| 4 | ccMantagheh | int | NO | | Region id |
| 5 | ccMarkazPakhsh | int | NO | | Distribution center id |
| 6 | ccForoshandeh | int | NO | | Salesperson id |
| 7 | NoeForoshandeh | tinyint | NO | | Salesperson type |
| 8 | ccAfradForoshandeh | int | YES | | Salesperson person (Afrad) id |
| 9 | ccMoshtary | int | NO | | Customer id |
| 10 | ccShahrMoshtary | int | YES | | Customer city id |
| 11 | ShomarehElamMarjoee | int | NO | | Return declaration number |
| 12 | TarikhElamMarjoee | datetime | NO | | Declaration date |
| 13 | ccDarkhastFaktor | bigint | YES | | Related original order/invoice |
| 14 | NextFaktor | tinyint | NO | | Affects next invoice flag |
| 15 | CodeVazeiat | tinyint | NO | | Workflow/status code |
| 16 | Elat | nvarchar(50) | NO | | Status / return reason short text |
| 17 | DateVorod | datetime | NO | | Insert datetime |
