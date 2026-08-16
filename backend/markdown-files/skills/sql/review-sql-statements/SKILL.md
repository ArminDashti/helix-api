---
name: Review SQL statements
description: Approve or reject each SQL statement with SELECT-only and anti-heavy
  checks, then fetch rows
---

# Review SQL statements

1. Parse each statement; classify as SELECT vs forbidden.
2. Check object allowlist against `tables.md`.
3. Check heaviness heuristics (limits, SELECT *, joins).
4. On approve, fetch the rows. On reject, return `failed` with reasons.
