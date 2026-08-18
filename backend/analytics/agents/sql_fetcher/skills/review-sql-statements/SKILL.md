---
name: Review SQL statements
description: Approve or reject each SQL statement with SELECT-only, anti-heavy, and fast-query
  checks, then fetch rows
---

# Review SQL statements

1. Parse each statement; classify as SELECT vs forbidden.
2. Check object allowlist against `tables.md`.
3. Check heaviness: `TOP`/`FETCH` on the final SELECT, no `SELECT *`, no cartesian joins.
4. Check speed: header filtered before joining lines; sargable `ccMarkazPakhsh` / `Sal` / `TarikhFaktor`; no scalar functions on those columns; no double unfiltered fact scan.
5. On approve, fetch the rows. On reject, return `fail` with reasons — do not execute.
