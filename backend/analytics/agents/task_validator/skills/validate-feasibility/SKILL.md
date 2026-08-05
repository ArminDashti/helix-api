---
name: validate-feasibility
description: Check prompt and mode against Helix capabilities and allowlisted schema
---

# Validate feasibility

1. Parse the user ask and mode.
2. Map the ask to allowlisted objects in `tables.md` (or conclude none fit).
3. Confirm the ask does not require forbidden operations (writes, unbounded dumps, unlisted PII stores).
4. Emit `feasible: true|false` with reasons.
