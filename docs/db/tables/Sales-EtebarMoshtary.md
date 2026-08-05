# Sales.EtebarMoshtary

## Table overview

Customer credit (Etebar) snapshot per distribution center. Stores calculated credit limit, purchase/return stats, open invoices, bounced checks, risk coefficients, and block state used to allow or block new sales.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccEtebarMoshtary | bigint | NO | PK, Identity | Credit record primary key |
| 2 | ccMoshtary | int | NO | | Customer id |
| 3 | ccMarkazpakhsh | tinyint | NO | | Distribution center id |
| 4 | AzTarikh | datetime | NO | | Calculation period from |
| 5 | TaTarikh | datetime | NO | | Calculation period to |
| 6 | TedadeKharid | int | NO | | Purchase count in period |
| 7 | TedadMarjooee | int | NO | | Return count in period |
| 8 | MablaghKharidKhales | float | NO | | Net purchase amount |
| 9 | MianginMablaghKharidKhales | float | NO | | Average net purchase |
| 10 | TedadFaktorBaz | smallint | NO | | Open invoice count |
| 11 | MablaghMandehMoshtary | float | NO | | Outstanding customer balance |
| 12 | ZaribMalekiat | float | NO | | Ownership coefficient |
| 13 | zaribRisk | float | YES | | Risk coefficient |
| 14 | MizanEtebar | float | NO | | Computed credit limit |
| 15 | TarikhMohasebeh | datetime | NO | | Credit calculation date |
| 16 | MizanEtebarTmp | float | YES | | Temporary credit amount |
| 17 | ccDarkhastFaktor | int | YES | | Related order triggering recalc |
| 18 | ccDariaftPardakhst | int | YES | | Related receipt/payment id |
| 19 | CheckBargashti | tinyint | NO | | Has bounced check flag |
| 20 | CheckBargashtiHoghoghi | tinyint | YES | | Bounced check escalated to legal |
| 21 | FaktorBazHoghoghi | tinyint | YES | | Open invoice escalated to legal |
| 22 | FaktorBazDay | int | YES | | Days of oldest open invoice |
| 23 | checkDay | int | YES | | Days related to bounced check |
| 24 | FromDate | datetime | YES | | Alternate period from |
| 25 | EndDate | datetime | YES | | Alternate period to |
| 26 | Blocked | tinyint | YES | | Credit-blocked flag |
| 27 | FaktorHoghoghiHistory | int | YES | | Legal invoice history counter |
| 28 | CheckHoghoghiHistory | int | YES | | Legal check history counter |
| 29 | ElatBlocked | nvarchar(20) | YES | | Block reason code/text |
| 30 | GradeMoshtary | nvarchar(5) | YES | | Customer credit grade |
| 31 | MablaghAsnadEtebariDarJaryanVosol | float | YES | | Credit docs in collection |
| 32 | MablaghMandehCheckBargashti | float | YES | | Remaining bounced-check amount |
| 33 | MablaghMandehCheckBargashtiHoghoghiShodeh | float | YES | | Remaining legal bounced checks |
| 34 | MablaghMandehFaktorBargashtiHoghoghi | float | YES | | Remaining legal returned invoices |
| 35 | CountMahForosh | int | YES | | Months with sales count |
| 36 | TarikhAsnadEtebariDarJaryanVosol | datetime | YES | | Date of credit docs in collection |
| 37 | IsPrivate | int | YES | | Private/special credit flag |
| 38 | MablaghKharjeCheck | float | YES | | Check expense / fee amount |
