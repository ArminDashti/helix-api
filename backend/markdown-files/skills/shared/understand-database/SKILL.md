---
name: Understand database
description: Read the warehouse catalog and pick allowlisted objects, grain, joins, and cheap filters
---

# Understand database

## When to use

- Any prompt that needs warehouse data
- Before writing SQL, a grid, a chart, or an analytical report

## Instructions

1. Read `tables.md` (and table docs when present). Use only allowlisted objects.
2. Pick grain (one row means what) and join keys. Name metrics and filters in catalog terms.
3. Name the **driving table** and the **cheapest filters** first: `ccMarkazPakhsh` for named centers, `Sal` / `TarikhFaktor` for time, `ccKala` for products. Resolve names to ids on a small lookup, then `IN` on the fact key.
4. Join `Sales.DarkhastFaktorSatr` only after the header is filtered. Do not plan a full-history scan unless the user asked for all years.
5. If no allowlisted object fits, stop as infeasible. Do not invent tables or columns.
