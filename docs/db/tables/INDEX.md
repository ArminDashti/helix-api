# Sales tables index

Browse by topic or Finglish name, then open the linked `.md` file for full column details.

## Quick find

| Looking for… | Keywords / aliases | Table | Doc |
|--------------|--------------------|-------|-----|
| Customer master | Moshtary, customer, client, GLN, HIX | `Sales.Moshtary` | [Sales-Moshtary.md](Sales-Moshtary.md) |
| Salesperson / visitor | Foroshandeh, seller, visitor, tablet device | `Sales.Foroshandeh` | [Sales-Foroshandeh.md](Sales-Foroshandeh.md) |
| Sales order / invoice header | Darkhast Faktor, order, invoice, faktor, GPS visit | `Sales.DarkhastFaktor` | [Sales-DarkhastFaktor.md](Sales-DarkhastFaktor.md) |
| Order / invoice lines | Darkhast Faktor Satr, line item, Tedad, batch, Jayezeh | `Sales.DarkhastFaktorSatr` | [Sales-DarkhastFaktorSatr.md](Sales-DarkhastFaktorSatr.md) |
| Product sell price | Kala Gheymat Forosh, price list, MablaghForosh | `Sales.KalaGheymatForosh` | [Sales-KalaGheymatForosh.md](Sales-KalaGheymatForosh.md) |
| Who visits which customer | Foroshandeh Moshtary, assignment, RoozVizit | `Sales.ForoshandehMoshtary` | [Sales-ForoshandehMoshtary.md](Sales-ForoshandehMoshtary.md) |
| Visit route | Masir, path, route, ToorVisit | `Sales.Masir` | [Sales-Masir.md](Sales-Masir.md) |
| Customer return | Elam Marjoee, return, marjoee | `Sales.ElamMarjoee` | [Sales-ElamMarjoee.md](Sales-ElamMarjoee.md) |
| Customer credit / block | Etebar Moshtary, credit limit, bounced check | `Sales.EtebarMoshtary` | [Sales-EtebarMoshtary.md](Sales-EtebarMoshtary.md) |
| Invoice printing | Print Faktor, print range, report template | `Sales.PrintFaktor` | [Sales-PrintFaktor.md](Sales-PrintFaktor.md) |

## By sales flow

```text
Moshtary ──► ForoshandehMoshtary ──► Masir
    │              │
    │              └──► Foroshandeh
    │
    ├──► EtebarMoshtary          (credit check)
    │
    └──► DarkhastFaktor ──► DarkhastFaktorSatr
              │                      ▲
              │                      │ prices from
              │               KalaGheymatForosh
              │
              ├──► PrintFaktor       (print invoices)
              └──► ElamMarjoee       (returns)
```

1. **Master data** — [Moshtary](Sales-Moshtary.md), [Foroshandeh](Sales-Foroshandeh.md), [Masir](Sales-Masir.md), [ForoshandehMoshtary](Sales-ForoshandehMoshtary.md), [KalaGheymatForosh](Sales-KalaGheymatForosh.md)
2. **Credit** — [EtebarMoshtary](Sales-EtebarMoshtary.md)
3. **Order → invoice** — [DarkhastFaktor](Sales-DarkhastFaktor.md), [DarkhastFaktorSatr](Sales-DarkhastFaktorSatr.md), [PrintFaktor](Sales-PrintFaktor.md)
4. **Returns** — [ElamMarjoee](Sales-ElamMarjoee.md)

## Alphabetical (schema-table)

| Doc file | Schema.Table | One-line purpose |
|----------|--------------|------------------|
| [Sales-DarkhastFaktor.md](Sales-DarkhastFaktor.md) | `Sales.DarkhastFaktor` | Order / invoice request header |
| [Sales-DarkhastFaktorSatr.md](Sales-DarkhastFaktorSatr.md) | `Sales.DarkhastFaktorSatr` | Order / invoice line items |
| [Sales-ElamMarjoee.md](Sales-ElamMarjoee.md) | `Sales.ElamMarjoee` | Return declaration header |
| [Sales-EtebarMoshtary.md](Sales-EtebarMoshtary.md) | `Sales.EtebarMoshtary` | Customer credit snapshot & block |
| [Sales-Foroshandeh.md](Sales-Foroshandeh.md) | `Sales.Foroshandeh` | Salesperson master |
| [Sales-ForoshandehMoshtary.md](Sales-ForoshandehMoshtary.md) | `Sales.ForoshandehMoshtary` | Salesperson–customer–route link |
| [Sales-KalaGheymatForosh.md](Sales-KalaGheymatForosh.md) | `Sales.KalaGheymatForosh` | Product selling price list |
| [Sales-Masir.md](Sales-Masir.md) | `Sales.Masir` | Visit route definition |
| [Sales-Moshtary.md](Sales-Moshtary.md) | `Sales.Moshtary` | Customer master |
| [Sales-PrintFaktor.md](Sales-PrintFaktor.md) | `Sales.PrintFaktor` | Invoice print log / params |

## Naming tip

Most names are Finglish: **Moshtary** = customer, **Foroshandeh** = salesperson, **Darkhast Faktor** = invoice request, **Satr** = line, **Masir** = route, **Etebar** = credit, **Marjoee** = return, **Gheymat Forosh** = sell price.
