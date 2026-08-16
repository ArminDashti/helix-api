# Project Experience Log

Recorded problems, issues, and learnings as question-and-answer entries.

---

## Q: Why did Helix API report "pyodbc is not installed" even though it was in requirements.txt?

**Date:** 2026-08-16  
**Tags:** pyodbc, python, wheels, venv

### A:

`pyodbc` was already listed in `backend/requirements.txt`, but the local `.venv` used CPython 3.15 rc1. pyodbc 5.3.0 publishes Windows wheels only through 3.14, so pip downloaded the sdist and failed without MSVC.

Fix: install CPython 3.12, recreate `.venv` with `Python312\python.exe -m venv .venv`, then `pip install -r backend/requirements.txt`. Verify with `import pyodbc`. Pin `.python-version` to `3.12`. Django `AppConfig.ready()` calls `ensure_pyodbc_installed()` so a missing package is installed at boot when a wheel exists.
