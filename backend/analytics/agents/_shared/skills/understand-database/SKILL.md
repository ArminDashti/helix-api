---
name: understand-database
description: Read the warehouse catalog and pick allowlisted objects, grain, and joins
---

# Understand database

## When to use

- Any prompt that needs warehouse data
- Before writing SQL, a grid, a chart, or an analytical report

## Instructions

1. Read `tables.md` (and table docs when present). Use only allowlisted objects.
2. Pick grain (one row means what) and join keys. Name metrics and filters in catalog terms.
3. If no allowlisted object fits, stop as infeasible. Do not invent tables or columns.
