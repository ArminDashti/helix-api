---
name: Security
---
# Shared security rules

Apply to every agent in the Helix pipeline.

1. Never invent database objects outside `schema/tables.md`.
2. Never request or generate credentials, passwords, or auth-table access.
3. SQL must be SELECT-only; writes, DDL, and EXEC are forbidden (enforced by the SQL agent and `validate_select`).
4. Do not instruct the sandbox to install packages (`pip`, `conda`, etc.). Use only pre-installed allowlisted libraries.
5. Honor `mode` via the output contract (`analytical_report`, `grid`, `chart`, `analytical_report_chart`, `auto`). Do not invent extra product types.
