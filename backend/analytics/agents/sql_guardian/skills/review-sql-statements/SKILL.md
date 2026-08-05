---
name: review-sql-statements
description: Approve or reject each SQL statement with SELECT-only and anti-heavy checks
---

# Review SQL statements

1. Parse each statement; classify as SELECT vs forbidden.
2. Check object allowlist against `tables.md`.
3. Check heaviness heuristics (limits, SELECT *, joins).
4. Return approve/reject with reasons.
