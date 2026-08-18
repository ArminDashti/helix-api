# Project Experience Log

Recorded problems, issues, and learnings as question-and-answer entries.

---

## Q: Why did Helix API report "pyodbc is not installed" even though it was in requirements.txt?

**Date:** 2026-08-16  
**Tags:** pyodbc, python, wheels, venv

### A:

`pyodbc` was already listed in `backend/requirements.txt`, but the local `.venv` used CPython 3.15 rc1. pyodbc 5.3.0 publishes Windows wheels only through 3.14, so pip downloaded the sdist and failed without MSVC.

Fix: install CPython 3.12, recreate `.venv` with `Python312\python.exe -m venv .venv`, then `pip install -r backend/requirements.txt`. Verify with `import pyodbc`. Pin `.python-version` to `3.12`. Django `AppConfig.ready()` calls `ensure_pyodbc_installed()` so a missing package is installed at boot when a wheel exists.

---

## Q: Why did POST /api/chat return HTTP 400 with "pyodbc.Error returned a result with an exception set"?

**Date:** 2026-08-18  
**Tags:** pyodbc, odbc, sql-server, chat

### A:

That SystemError is Python wrapping a second ODBC error. SQL Server dropped the TDS session (08S01 communication link failure). Two follow-up actions then hid the original error:

1. `raise ValueError(...) from exc` while `exc` is still a live `pyodbc.Error`
2. Calling pyodbc `close()` (or `__exit__`) while that ODBC exception is still set

Either one becomes: `<class 'pyodbc.Error'> returned a result with an exception set`. The chat pipeline stringified that SystemError and `/api/chat` returned HTTP 400.

Fix: skip `close()` when `__exit__` already has an exception; do not chain `from exc`; stringify driver errors from `exc.args` first; treat "exception set" as a retryable link failure; map warehouse/driver failures on `/api/chat` to HTTP 502 with a plain message. `docker-compose.yml` must have a `build:` block — `image:` alone means `docker compose up --force-recreate` restarts the stale image.

Do not assign `conn.close = ...` — pyodbc marks `close` read-only. Use a wrapper class instead.

