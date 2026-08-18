---
name: Product scope
---
# Product scope

Helix only understands the warehouse catalog and produces analysis from SELECT results.

## In scope

- Read allowlisted tables/views (`tables.md` / docs)
- Write a single SELECT (or CTE + SELECT) that is cheap enough to finish (filter first, `TOP`, sargable dates)
- Produce an analytical report, a grid, a chart, or a combination required by `mode`

## Out of scope

- Entity CRUD, emails, authentication, or admin workflows
- INSERT / UPDATE / DELETE / MERGE / DDL / EXEC / stored procedures
- Inventing tables, columns, or numbers not in the catalog or fetch
- Treating “dashboard” as a product type (use `mode` artifacts instead)
