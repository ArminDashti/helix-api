# Shared security rules

Apply to every agent in the Helix pipeline.

1. Never invent database objects outside `schema/tables.md`.
2. Never request or generate credentials, passwords, or auth tables access.
3. SQL must be SELECT-only; writes and DDL are forbidden (enforced later by SQL Guardian + sqlglot).
4. Do not instruct the sandbox to install packages (`pip`, `conda`, etc.). Use only pre-installed allowlisted libraries.
5. Respect UI mode: `analysis` (text only), `chart` (ECharts only), `both` (chart then explanation).
