# Database catalog

Helix runs SELECT-only analysis against the **connected database** (SQL Server, PostgreSQL, SQLite sample, or other configured engine). Use `schema.table` names and column names from **Live catalog** (introspected at runtime). Documented sections below apply only when those objects exist in the connected database.

Never invent tables, views, or columns.

# Query speed

- Filter the driving / fact table first with sargable predicates on keys the user named.
- Bound every SELECT with `TOP`, `FETCH`, or `LIMIT` unless config allows otherwise.
- Join lookup tables only for display columns; resolve names to ids on small lookups when needed.
- Default to a recent time window when the user did not ask for all history.
- Rankings: filter, aggregate, window rank, keep top row per group, outer bound.

# Catalog

## Warehouse.Anbar

- **Kind:** table
- **Description:** Warehouse master. Use for warehouse counts by type.

| Column | Description |
|--------|-------------|
| ccAnbar | Warehouse primary key |
| ccMarkazPakhsh | Distribution center id |
| NameAnbar | Warehouse name |
| CodeNoeAnbar | Warehouse type code |
| ccAddress | Address id |
| Telephone | Phone |
| Fax | Fax |
| CodeNoeSys | System type code |
| CodeVazeiat | Status code |
| Anbarak | Sub-warehouse flag |
| NopWarehouseId | External warehouse id |
| GLN | Global location number |

## Warehouse.Kala

- **Kind:** table
- **Description:** Product master for product names (نام کالا). Join by `ccKala`.

| Column | Description |
|--------|-------------|
| ccKala | Product id |
| NameKala | Product name |

## Global.MarkazPakhsh

- **Kind:** table
- **Description:** Distribution center master. Resolve مرکز names (کرمان, تهران1) to `ccMarkazPakhsh` here, then filter the fact table. Use exact `NameMarkazPakhsh`; `LIKE N'%کرمان%'` also matches کرمانشاه.

| Column | Description |
|--------|-------------|
| ccMarkazPakhsh | Distribution center id |
| NameMarkazPakhsh | Center display name |

## Sales.Moshtary

- **Kind:** table
- **Description:** Customer master (Moshtary).

| Column | Description |
|--------|-------------|
| ccMoshtary | Customer primary key |
| NameMoshtary | Customer name |
| NameTablo | Storefront name |
| Telephone | Phone |
| CodeVazeiat | Status code |
| EtebarKol | Total credit limit |
| GLN | Global location number |

## Sales.Foroshandeh

- **Kind:** table
- **Description:** Salesperson (Foroshandeh) master per distribution center.

| Column | Description |
|--------|-------------|
| ccForoshandeh | Salesperson primary key |
| ccMarkazPakhsh | Distribution center id |
| ccAfrad | Person id |
| CodeVazeiat | Status code |

## Sales.DarkhastFaktor

- **Kind:** table
- **Description:** Sales order / invoice request header. Join lines on `ccDarkhastFaktor` + `Sal`.

| Column | Description |
|--------|-------------|
| ccDarkhastFaktor | Order/invoice request id |
| Sal | Jalali year part of key (1405, not Gregorian 2026). Filter this for Iranian years. |
| ccMarkazPakhsh | Distribution center id |
| ccForoshandeh | Salesperson id |
| ccMoshtary | Customer id |
| ShomarehFaktor | Invoice number |
| TarikhFaktor | Gregorian invoice datetime. Never YEAR(TarikhFaktor)=1405. For تیر 1405 use a Gregorian range (about 2026-06-22 to 2026-07-22). |
| MablaghKolFaktor | Gross invoice amount |
| MablaghKhalesFaktor | Net invoice amount |
| CodeVazeiat | Document status |

## Sales.DarkhastFaktorSatr

- **Kind:** table
- **Description:** Sales order / invoice line items (the Pakhsh equivalent of order detail). Parent is `Sales.DarkhastFaktor`.

| Column | Description |
|--------|-------------|
| ccDarkhastFaktor | Parent order/invoice request id |
| ccDarkhastFaktorSatr | Line primary key |
| Sal | Year (with parent key) |
| ccKala | Product id |
| Tedad1 | Quantity in unit 1 |
| MablaghForosh | Sale amount / unit price base |
| MablaghForoshKhalesKala | Net sale amount for product |
| Maliat | Tax amount |

## Sales.KalaGheymatForosh

- **Kind:** table
- **Description:** Product selling price list.

| Column | Description |
|--------|-------------|
| ccKala | Product id |
| MablaghForosh | Sell price |

## Sales.ForoshandehMoshtary

- **Kind:** table
- **Description:** Salesperson–customer–route assignment.

| Column | Description |
|--------|-------------|
| ccForoshandeh | Salesperson id |
| ccMoshtary | Customer id |

## Sales.Masir

- **Kind:** table
- **Description:** Visit route definition.

| Column | Description |
|--------|-------------|
| ccMasir | Route primary key |
| ccMarkazPakhsh | Distribution center id |

## Sales.ElamMarjoee

- **Kind:** table
- **Description:** Customer return declaration header.

| Column | Description |
|--------|-------------|
| ccElamMarjoee | Return header id |
| ccMarkazPakhsh | Distribution center id |
| ccMoshtary | Customer id |

## Sales.EtebarMoshtary

- **Kind:** table
- **Description:** Customer credit snapshot and block.

| Column | Description |
|--------|-------------|
| ccMoshtary | Customer id |
| ccMarkazPakhsh | Distribution center id |

## Sales.PrintFaktor

- **Kind:** table
- **Description:** Invoice print log / parameters.

| Column | Description |
|--------|-------------|
| ccMarkazPakhsh | Distribution center id |
| ShomarehFaktorAz | Invoice number from |
| ShomarehFaktorTa | Invoice number to |
