---
name: Understand database
description: Read references and live catalog; pick allowlisted objects, grain, joins,
  and cheap filters
---

# Understand database

## When to use

- Any prompt that needs warehouse data
- Before writing SQL, a grid, a chart, or an analytical report

## Instructions

1. Read every assigned reference and the **live catalog** (introspected columns from the connected database). Use only listed objects and columns.
2. When static docs and live catalog differ, prefer the live catalog.
3. Pick grain (one row means what) and join keys. Name metrics and filters in catalog terms.
4. Name the **driving table** and the **cheapest filters** first. Resolve display names to ids on a small lookup when needed, then filter the fact key.
5. Join detail tables only after the header or driving table is filtered. Do not plan a full-history scan unless the user asked for all years.
6. Iranian calendar: `Sal` is Jalali year; `TarikhFaktor` is Gregorian. Convert تیر/خرداد + 1405 to a Gregorian range. Never filter YEAR(TarikhFaktor)=1405.
7. Center names live on `Global.MarkazPakhsh`. Exact match; کرمان is not کرمانشاه.
8. If no catalog object fits, stop as infeasible. Do not invent tables or columns.
