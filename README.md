# Helix API

Django REST/SSE backend for Helix — LLM-powered data analysis and charting agent pipeline.

Companion UI: [helix-webui](https://github.com/ArminDashti/helix-webui).

## Run locally

```bash
cd backend
pip install -r requirements.txt
copy ..\helix.config.example.yaml ..\helix.config.yaml
# OpenRouter: set OPENROUTER_TOKEN in your environment (not in helix.config.yaml)
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Editable Markdown lives in `backend/markdown-files/` (seeded from `analytics/agents` on first start).

## Docker

```bash
docker build -t helix-api:latest -f dockerfile .
# Ensure helix.config.yaml exists, then:
docker compose up -d
```

API listens on port 8000 by default.

## Agent pipeline

1. Task Validator → 2. Solution Strategist → 3. Technical Architect → 4. Code Builder → 5. SQL Guardian → 6. Implementation Auditor → 7. Response Publisher

See `backend/analytics/agents/registry.md`.
