# Chat HTTP 400 Pyodbc

| Field | Value |
|-------|-------|
| Agent | `Auto` |
| Date | `2026-08-18` |
| Time | `15:48:00` |
| Device | `PC-ARMIN` |

## Skills

`transform-human-prompt-to-agent-understanding` / `accept-reject-human-prompt` / `log-human-prompt` / `webui-debug-functionality` / `helix-product-scope` / `suggest-for-improving` / `dictionary-by-armin` / `report-to-human-in-end-of-response` / `log-session`

## Rules

`user-pass-default` / `restart-api-when-needed` / `helix-product-scope`

---

## Transcript

### Agent

The HTTP 400 on POST /api/chat was a warehouse ODBC failure turned into a Python SystemError. Closing or chaining a live pyodbc.Error produced "returned a result with an exception set", and the Docker API image was stale so that text came back as 400. The API now skips close while an ODBC exception is pending, does not chain `from exc`, maps the failure to HTTP 502 with a plain message, and the helix-api container on :8000 was rebuilt. Retry the same chat; a still-too-heavy SELECT will show a clear 502 instead of this 400.
