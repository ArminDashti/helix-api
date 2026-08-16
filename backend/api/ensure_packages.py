"""Install required Python packages into the running interpreter when missing."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

PYODBC_SPEC = "pyodbc>=5.0,<6"


def _has_published_pyodbc_wheel() -> bool:
    # pyodbc 5.3 ships wheels through CPython 3.14, not 3.15.
    return sys.version_info < (3, 15)


def ensure_pyodbc_installed() -> Any:
    try:
        import pyodbc  # type: ignore
    except ImportError as exc:
        detail = str(exc)
        if "libodbc" in detail:
            raise ValueError(
                "unixODBC is missing (libodbc.so). Install unixodbc and "
                "ODBC Driver 18 in the API image."
            ) from exc
        if not _has_published_pyodbc_wheel():
            raise ValueError(
                "pyodbc has no binary wheel for this Python version. "
                "Use CPython 3.12 (same as the API Docker image) and "
                f"pip install {PYODBC_SPEC}."
            ) from exc
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", PYODBC_SPEC],
            )
        except Exception as install_exc:
            raise ValueError(
                "pyodbc is not installed and pip install failed. "
                f"Run: pip install {PYODBC_SPEC}"
            ) from install_exc
        try:
            import pyodbc  # type: ignore
        except ImportError as retry_exc:
            raise ValueError(
                f"pyodbc is not installed. Run: pip install {PYODBC_SPEC}"
            ) from retry_exc
    return pyodbc
