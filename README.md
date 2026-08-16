# Helix API

Django REST/SSE backend for Helix — LLM-powered data analysis and charting agent pipeline.

Companion UI: [helix-webui](https://github.com/ArminDashti/helix-webui).

## Run locally

Use **CPython 3.12** (same as the Docker image). `pyodbc` ships wheels through 3.14; Python 3.15 has no wheel and cannot install without a C++ compiler.

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
copy helix.config.example.yaml helix.config.yaml
cd backend
# Paste the OpenRouter or Cursor API key in the web UI Settings page.
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Editable Markdown lives in `backend/markdown-files/` (seeded from `analytics/agents` on first start).

By default the analytics connection uses a **sample SQLite AdventureWorks LT database** (`backend/data/helix-sample.sqlite`, downloaded on first API start) so Docs, DB Explorer, and agent runs have real customer/product/order data. Switch to PostgreSQL/SQL Server under Settings when you have a real warehouse.

## Docker

```bash
docker build -t helix-api:latest -f dockerfile .
# Ensure helix.config.yaml exists, then:
docker compose up -d
```

API listens on port 8000 by default.

## Agent pipeline

1. Task Validator → 2. Solution Strategist → 3. Technical Architect → 4. Code Builder → 5. SQL → 6. Implementation Auditor → 7. Response Publisher

Agents use assigned rules and skills only (no instruction files). Analysis runs fetch real warehouse rows via the SQL agent and return charts/reports from those rows.

See `backend/analytics/agents/registry.md`.
