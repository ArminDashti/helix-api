# Pakhsh warehouse catalog

The live warehouse is Pakhsh (SQL Server). Use `schema.table` names from this catalog.
AdventureWorks / `SalesLT.*` objects do not exist here.

Other live Pakhsh schemas may also be queried (Sales, Warehouse, Global, Purchase, FinancialAccounting, AssetAccounting, Budget). Names are Finglish (Moshtary = customer, Foroshandeh = salesperson, Darkhast Faktor = invoice request, Satr = line).

Primary objects:

- Warehouse.Anbar
- Sales.Moshtary
- Sales.Foroshandeh
- Sales.DarkhastFaktor
- Sales.DarkhastFaktorSatr
- Sales.KalaGheymatForosh
- Sales.ForoshandehMoshtary
- Sales.Masir
- Sales.ElamMarjoee
- Sales.EtebarMoshtary
- Sales.PrintFaktor

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
| Sal | Year part of key |
| ccMarkazPakhsh | Distribution center id |
| ccForoshandeh | Salesperson id |
| ccMoshtary | Customer id |
| ShomarehFaktor | Invoice number |
| TarikhFaktor | Invoice date |
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
