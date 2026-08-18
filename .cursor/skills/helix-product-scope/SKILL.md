---
name: helix-product-scope
description: >-
  Keeps Helix API work as warehouse SELECT plus report, grid, analysis, or
  chart artifacts. Use when implementing or reviewing helix-api features,
  pipeline markdown, SQL execution, or run payloads.
disable-model-invocation: false
metadata:
  version: "1.0.0"
  author: Armin Dashti
  category: product
  tags: [helix, warehouse, report, grid, chart, select-only]
  last_updated: "2026-08-16 15:10:00"
  uuid: a1f3c8e0-9d24-4b6a-8e71-5c2d90f4b118
---

# Helix product scope

## When

- Implementing or reviewing helix-api (pipeline, SQL, payloads, agent markdown)
- User asks for a new API feature, mode, or agent skill/rule
- Checking whether a change belongs in a reporting/charting warehouse app

## How

1. Treat the product as: understand the warehouse catalog, run SELECT-only SQL, emit `{ text_report, grid, echarts_option }` per `mode`.
2. Match modes to `_package_result` and `VALID_MODES` (`auto`, `chart`, `grid`, `analytical_report`, `analytical_report_chart`; aliases `analysis`/`research`/`both`).
3. Change pipeline markdown in `backend/analytics/agents/` and copy into `backend/markdown-files/` (runtime does not refresh if files already exist).
4. Keep `validate_select` / FORBIDDEN_SQL. Do not add CRUD resources, write SQL, EXEC, or a dashboard type.
5. Point Guardian, SQL fetcher, Response builder, and Validator at shared rules `product-scope`, `security`, `output-contract` and skills `understand-database`, `generate-grid`, `generate-analytical-report`, `echarts-response`.

## Always

1. Update both markdown trees when changing in-app agent rules or skills.

## Never

1. Expand the API into business-entity REST or stored-procedure reporting.

## Example

**Example 1** — New analysis mode

- Input: "Add a dashboard mode."
- Output: reject as a new product type; use `analytical_report_chart` or `auto` plus existing artifacts.

**Example 2** — Grid from SQL

- Input: "Show order lines as a table."
- Output: `mode=grid`; SELECT allowlisted objects; package `{ columns, rows }`.

**Example 3** — Write API

- Input: "Add POST /customers to insert a row."
- Output: out of scope. Do not add the endpoint.

**Example 4** — Chart from fetch

- Input: "Bar chart of revenue by region."
- Output: `mode=chart`, `chart_type=bar`, `build_echarts_option` from SELECT rows.

**Example 5** — Stale markdown

- Input: "Update output-contract for grid."
- Output: edit `backend/analytics/agents/_shared/rules/01-output-contract.md` and `backend/markdown-files/rules/output-contract.md`.

**Example 6** — EXEC

- Input: "Run sp_SalesReport."
- Output: reject. SELECT-only; no EXEC / stored procedures.
