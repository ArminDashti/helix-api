# Sales.Foroshandeh

## Table overview

Salesperson (Foroshandeh) master per distribution center. Defines who sells for a MarkazPakhsh, risk limits on bounced checks / open invoices, and links to person (`ccAfrad`) and sales group.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccMarkazPakhsh | int | NO | | Distribution center id |
| 2 | ccForoshandeh | int | NO | PK, Identity | Salesperson primary key |
| 3 | NoeForoshandeh | tinyint | NO | | Salesperson type code |
| 4 | RoozMojaz | int | NO | | Allowed visit/work days mask or count |
| 5 | MaxTedadCheckBargashty | int | NO | | Max allowed bounced-check count |
| 6 | MaxMablaghCheckBargashty | float | NO | | Max allowed bounced-check amount |
| 7 | MaxModatCheckBargashty | int | NO | | Max allowed bounced-check age (days) |
| 8 | MaxTedadFaktorBaz | int | NO | | Max open invoice count allowed |
| 9 | MaxMablaghFaktorBaz | float | NO | | Max open invoice amount allowed |
| 10 | CodeVazeiat | tinyint | NO | | Status (active/inactive, etc.) |
| 11 | CodeForoshandehOld | nvarchar(10) | NO | | Legacy salesperson code |
| 12 | SharhForoshandeh | nvarchar(50) | NO | | Display name / description |
| 13 | ccAfrad | int | YES | | Linked person (Afrad) id |
| 14 | ccGorohForosh | int | YES | | Sales group id |
| 15 | MobileNumber | nvarchar(11) | YES | | Mobile phone |
| 16 | TypeForoshandeh | nvarchar(2) | YES | | Extra salesperson type tag |
| 17 | DeviceID | nvarchar(20) | YES | | Tablet/device identifier |
