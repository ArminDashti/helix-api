# Shared security rules

Apply to every agent in the Helix pipeline. Also follow `references/base-instruction.md`.

1. Never invent database objects outside `tables.md` (Allowed objects + Catalog).
2. Never request or generate credentials, passwords, connection secrets, or auth-table access.
3. SQL must be SELECT-only; writes and DDL are forbidden (enforced later by SQL Guardian + deterministic checks).
4. Do not instruct the sandbox to install packages (`pip`, `conda`, etc.). Use only pre-installed allowlisted libraries.
5. Respect UI mode: `analysis` (text only), `chart` (ECharts only), `both` (chart then explanation).
6. Do not exfiltrate or echo secrets from config, environment, or prior messages.
7. If a request conflicts with these rules, refuse and explain in plain language — do not propose a violating workaround.
