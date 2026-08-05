# Sales.DarkhastFaktorSatr

## Table overview

Line items of a sales order/invoice request. Each row is a product (`ccKala` / `ccKalaCode`) with quantities (Tedad1–3), sale price, discounts, tax, batch/expiry, and optional prize (Jayezeh) amounts. Parent is `DarkhastFaktor` via `ccDarkhastFaktor` + `Sal`.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccDarkhastFaktor | bigint | NO | | Parent order/invoice request id |
| 2 | ccDarkhastFaktorSatr | bigint | NO | PK, Identity | Line primary key |
| 3 | Sal | int | NO | PK | Year (with parent key) |
| 4 | ccKala | int | YES | | Product (Kala) id |
| 5 | ccKalaCode | int | YES | | Product code / SKU id |
| 6 | ShomarehBach | nvarchar(50) | YES | | Batch / lot number |
| 7 | TarikhTolid | datetime | YES | | Production date |
| 8 | TarikhEngheza | datetime | YES | | Expiry date |
| 9 | Tedad1 | float | NO | | Quantity in unit 1 |
| 10 | Tedad2 | float | NO | | Quantity in unit 2 |
| 11 | Tedad3 | float | NO | | Quantity in unit 3 |
| 12 | MablaghForosh | float | NO | | Sale amount / unit price base |
| 13 | MablaghTakhfifDarkhast | float | YES | | Discount on request line |
| 14 | MablaghTakhfifFaktor | float | YES | | Discount on invoice line |
| 15 | ccTafkikJoze | bigint | YES | | Partial picking / split link |
| 16 | MojodyGhabelForosh | float | YES | | Sellable stock at line time |
| 17 | DateVorod | datetime | NO | | Line insert datetime |
| 18 | CodeNoeKala | tinyint | NO | | Product kind (sale, free, prize, …) |
| 19 | ccTaminKonandeh | int | YES | | Supplier id |
| 20 | GheymatMiangin | float | NO | | Average cost/price |
| 21 | ccDarkhastFaktorSatrTaavoni | bigint | YES | | Linked cooperative line id |
| 22 | ccAfrad | int | YES | | Related person id |
| 23 | CodeVazeiat | tinyint | NO | | Line status |
| 24 | DarsadTakhfifTaavoni | float | YES | | Cooperative discount percent |
| 25 | ccUser | int | YES | | User who entered the line |
| 26 | MablaghTakhfifNaghdiVahed | float | YES | | Cash discount per unit |
| 27 | GheymatKharid | float | YES | | Purchase cost |
| 28 | DiscntType | int | YES | | Discount type |
| 29 | DiscntSubType | int | YES | | Discount subtype |
| 30 | TarikhFaktor | datetime | NO | | Invoice date on line |
| 31 | Maliat | float | NO | | Tax amount |
| 32 | Avarez | float | NO | | Duty / surcharge amount |
| 33 | TarikhEntry | datetime | NO | | Entry date |
| 34 | ModifiedDate | datetime | NO | | Last modify date |
| 35 | ccDarkhastFaktorSatrPPC | nvarchar(50) | YES | | PPC/tablet line id |
| 36 | GheymatMasrafKonandeh | decimal(18,0) | YES | | Consumer (MSRP) price |
| 37 | sentEmail | bit | YES | | Email-sent flag |
| 38 | MablaghTakhfifRialiSatr | float | YES | | Rial discount on line |
| 39 | NoeJayezeh | tinyint | YES | | Prize type on this line |
| 40 | MablaghForoshJayezeh | float | NO | | Sale amount related to prize |
| 41 | TakhfifJayezeh | float | NO | | Prize discount amount |
| 42 | MablaghTakhfifTahsilatSatr | float | YES | | Facility/education discount on line |
| 43 | MablaghForoshKhalesKala | float | NO | | Net sale amount for product |
