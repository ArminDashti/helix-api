---
name: sandbox-python
description: Write Python for the Helix sandbox using only pre-installed allowlisted libraries
---

# Sandbox Python

## When to use

- Implementing data load, transforms, ML (e.g. clustering), and chart/report artifact generation

## Instructions

1. Use only allowlisted, **already installed** packages (e.g. pandas, numpy, scikit-learn). Never `pip install` or download packages at runtime.
2. Load SQL Server data only through the sandbox SQL helper (SELECT + allowlist), not ad-hoc drivers that bypass guards.
3. Write agreed artifacts for the presenter (e.g. `echarts_option.json`, `text_report.md`) according to `mode`.
4. Keep queries bounded (TOP / FETCH / aggregates) — the SQL agent will reject heavy or non-SELECT SQL.
5. On sandbox errors, fix the code using the error message; do not change the technical plan unless the auditor requires it.
