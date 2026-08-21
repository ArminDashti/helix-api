"""Validate and execute SELECT statements for the SQL agent."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from .config_loader import get_database_settings, get_sql_settings
from .db_dialects import connect, list_tables
from .db_dialects.base import FORBIDDEN_SQL, cell_value
from .sample_database import SAMPLE_TABLES


def _dbg(location: str, message: str, data: dict[str, Any], hypothesis_id: str) -> None:
    # #region agent log
    payload = json.dumps(
        {
            "sessionId": "604d40",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
        },
        default=str,
    )
    for path in (
        r"C:\Users\armin\GitHub\helix-webui\debug-604d40.log",
        r"C:\Users\armin\GitHub\helix-webui\.cursor\debug-604d40.log",
        r"C:\Users\armin\GitHub\helix-api\debug-604d40.log",
    ):
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(payload + "\n")
        except Exception:
            pass
    try:
        import urllib.request

        req = urllib.request.Request(
            "http://127.0.0.1:7706/ingest/ac544aa8-f980-4348-bd8e-331cdfbc33b6",
            data=payload.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Debug-Session-Id": "604d40",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        pass
    # #endregion

_LIMIT = re.compile(r"\b(LIMIT|TOP|FETCH)\b", re.IGNORECASE)
_STAR = re.compile(r"SELECT\s+\*", re.IGNORECASE)
_SELECT = re.compile(r"^\s*(WITH\b[\s\S]+?\bSELECT\b|SELECT\b)", re.IGNORECASE)

_SALESLT_TABLES = (
    (re.compile(r"\[?SalesLT\]?\.\[?SalesOrderDetail\]?", re.IGNORECASE), "Sales.DarkhastFaktorSatr"),
    (re.compile(r"\[?SalesLT\]?\.\[?SalesOrderHeader\]?", re.IGNORECASE), "Sales.DarkhastFaktor"),
    (re.compile(r"\[?SalesLT\]?\.\[?Customer\]?", re.IGNORECASE), "Sales.Moshtary"),
)
_SALESLT_COLUMNS = (
    (re.compile(r"\bSalesOrderDetailID\b", re.IGNORECASE), "ccDarkhastFaktorSatr"),
    (re.compile(r"\bUnitPriceDiscount\b", re.IGNORECASE), "MablaghTakhfifFaktor"),
    (re.compile(r"\bSalesOrderID\b", re.IGNORECASE), "ccDarkhastFaktor"),
    (re.compile(r"\bOrderQty\b", re.IGNORECASE), "Tedad1"),
    (re.compile(r"\bProductID\b", re.IGNORECASE), "ccKala"),
    (re.compile(r"\bUnitPrice\b", re.IGNORECASE), "MablaghForosh"),
    (re.compile(r"\bLineTotal\b", re.IGNORECASE), "MablaghForoshKhalesKala"),
    (re.compile(r"\bCustomerID\b", re.IGNORECASE), "ccMoshtary"),
    (re.compile(r"\bCompanyName\b", re.IGNORECASE), "NameMoshtary"),
    (re.compile(r"\bTotalDue\b", re.IGNORECASE), "MablaghKhalesFaktor"),
    (re.compile(r"\bSubTotal\b", re.IGNORECASE), "MablaghKolFaktor"),
    (re.compile(r"\bOrderDate\b", re.IGNORECASE), "TarikhFaktor"),
)


def extract_sql(text: str) -> str:
    raw = (text or "").strip()
    fence = re.search(r"```(?:sql)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    if raw.lower().startswith("sql:"):
        raw = raw[4:].strip()
    return raw.rstrip(";").strip()


def _rewrite_saleslt_to_pakhsh(statement: str) -> str:
    if "saleslt" not in statement.lower():
        return statement
    rewritten = statement
    for pattern, target in _SALESLT_TABLES:
        rewritten = pattern.sub(target, rewritten)
    for pattern, target in _SALESLT_COLUMNS:
        rewritten = pattern.sub(target, rewritten)
    # #region agent log
    _dbg(
        "sql_execute.py:_rewrite_saleslt_to_pakhsh",
        "rewrote SalesLT identifiers to Pakhsh",
        {
            "before": statement[:500],
            "after": rewritten[:500],
            "changed": rewritten != statement,
        },
        "F",
    )
    # #endregion
    return rewritten


def _allowlisted_names() -> set[str]:
    sample_names = {t.lower() for t in SAMPLE_TABLES}
    names = set(sample_names)
    live_names: list[str] = []
    live_full: list[str] = []
    list_error = None
    try:
        for table in list_tables():
            live_name = str(table.get("name") or "").lower()
            names.add(live_name)
            live_names.append(live_name)
            live_full.append(str(table.get("full_name") or ""))
    except Exception as exc:  # noqa: BLE001 — debug: list_tables can fail
        list_error = f"{type(exc).__name__}: {_exception_text(exc)}"
    names.discard("")
    # #region agent log
    _dbg(
        "sql_execute.py:_allowlisted_names",
        "allowlist sample vs live",
        {
            "sample_has_salesorderdetail": "salesorderdetail" in sample_names,
            "live_has_salesorderdetail": "salesorderdetail" in live_names,
            "live_has_saleslt_salesorderdetail": any(
                n.lower() == "saleslt.salesorderdetail" for n in live_full
            ),
            "live_count": len(live_full),
            "live_full_preview": live_full[:40],
            "list_error": list_error,
        },
        "B",
    )
    # #endregion
    return names


def validate_select(
    sql: str,
    *,
    actor_allowed_tables: list[str] | None = None,
    actor_is_admin: bool = False,
) -> str:
    settings = get_sql_settings()
    statement = extract_sql(sql)
    if not statement:
        raise ValueError("SQL is empty")
    if ";" in statement:
        raise ValueError("Only one SQL statement is allowed")
    if FORBIDDEN_SQL.search(statement):
        raise ValueError("SQL must be SELECT-only")
    if not _SELECT.search(statement):
        raise ValueError("SQL must be a SELECT (or CTE + SELECT)")
    if settings["forbid_select_star"] and _STAR.search(statement):
        raise ValueError("SELECT * is forbidden")
    if settings["require_row_limit"] and not _LIMIT.search(statement):
        if "group by" not in statement.lower():
            raise ValueError("SQL must include LIMIT, TOP, or FETCH")
    from_tokens = re.findall(
        r"\b(?:FROM|JOIN)\s+(?:\[?([A-Za-z_][A-Za-z0-9_]*)\]?\.)?\[?([A-Za-z_][A-Za-z0-9_]*)\]?",
        statement,
        re.IGNORECASE,
    )
    enforce_allowlist = bool(settings.get("enforce_allowlist"))
    allowed: set[str] = set()
    if enforce_allowlist:
        allowed = _allowlisted_names()
    user_tables = {
        str(name).split(".")[-1].lower()
        for name in (actor_allowed_tables or [])
        if str(name).strip()
    }
    if not actor_is_admin and actor_allowed_tables is not None:
        if not user_tables:
            raise ValueError("User has no allowed warehouse tables")
        for _schema, table in from_tokens:
            if table.lower() not in user_tables:
                raise ValueError(f"Table {table} is not allowed for this user")
    # #region agent log
    _dbg(
        "sql_execute.py:validate_select",
        "FROM/JOIN tokens vs allowlist",
        {
            "enforce_allowlist": enforce_allowlist,
            "from_tokens": [{"schema": schema, "table": table} for schema, table in from_tokens],
            "allowed_contains_tables": {
                table.lower(): table.lower() in allowed for _, table in from_tokens
            },
            "user_tables": sorted(user_tables),
            "sql_preview": statement[:500],
        },
        "A",
    )
    # #endregion
    if enforce_allowlist:
        for schema, table in from_tokens:
            if table.lower() not in allowed:
                raise ValueError(f"Table {table} is not on the allowlist")
            _ = schema
    return statement


def _ensure_sqlserver_top(statement: str, max_rows: int) -> str:
    """Cap a SQL Server SELECT so the warehouse does not stream an unbounded result."""
    if _LIMIT.search(statement):
        return statement
    return re.sub(
        r"(?i)(\bSELECT)(\s+DISTINCT\b)?(?![\s\S]*\bSELECT\b)",
        rf"\1\2 TOP ({int(max_rows)})",
        statement,
        count=1,
    )


def _exception_text(exc: BaseException) -> str:
    """Stringify driver errors without calling str() first.

    str(pyodbc.Error) can itself raise SystemError when an ODBC exception is
    already set, which replaces the original 08S01 message.
    """
    chunks: list[str] = [type(exc).__name__]
    try:
        args = getattr(exc, "args", ())
        if args:
            chunks.append(" ".join(str(arg) for arg in args))
    except Exception:
        pass
    try:
        rendered = str(exc)
        if rendered and rendered not in chunks:
            chunks.append(rendered)
    except Exception as stringify_exc:
        chunks.append(type(stringify_exc).__name__)
        try:
            chunks.append(str(stringify_exc))
        except Exception:
            pass
    return " ".join(chunk for chunk in chunks if chunk)


def _is_communication_link_failure(exc: BaseException) -> bool:
    text = _exception_text(exc)
    lowered = text.lower()
    return (
        "08S01" in text
        or "communication link failure" in lowered
        or "returned a result with an exception set" in lowered
        or (type(exc).__name__ == "SystemError" and "pyodbc" in lowered)
    )


def _sql_error_message(exc: BaseException) -> str:
    if _is_communication_link_failure(exc):
        return (
            "SQL Server closed the connection while running the query. "
            "A SELECT without TOP can return too many rows, or the warehouse "
            "dropped a long query. Retry with a narrower SELECT (add TOP / WHERE)."
        )
    return _exception_text(exc)


def execute_select(
    sql: str,
    *,
    row_cap: int | None = None,
    actor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actor = actor or {}
    per_user: list[str] | None = None
    if (
        actor
        and not actor.get("is_admin")
        and not actor.get("is_guest")
        and not actor.get("unknown")
    ):
        per_user = list(actor.get("allowed_tables") or [])
    statement = validate_select(
        sql,
        actor_allowed_tables=per_user,
        actor_is_admin=bool(actor.get("is_admin")),
    )
    settings = get_sql_settings()
    max_rows = int(settings["max_rows"])
    if row_cap is not None:
        max_rows = max(1, min(max_rows, int(row_cap)))
    retries = int(settings["max_retries"])
    db = get_database_settings()
    from .db_dialects.base import normalize_engine

    if normalize_engine(db.get("engine")) == "sqlserver":
        statement = _ensure_sqlserver_top(statement, max_rows)
    # #region agent log
    _dbg(
        "sql_execute.py:execute_select",
        "execute before cursor",
        {
            "engine": db.get("engine"),
            "db_name": db.get("name"),
            "host": db.get("host"),
            "statement": statement[:800],
        },
        "C",
    )
    # #endregion
    fetched: list[Any] = []
    columns: list[str] = []
    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            with connect() as conn:
                cur = conn.cursor()
                cur.execute(statement)
                desc = cur.description or []
                columns = [str(col[0]) for col in desc]
                fetched = list(cur.fetchmany(max_rows))
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            # #region agent log
            _dbg(
                "sql_execute.py:execute_select",
                "execute failed",
                {
                    "engine": db.get("engine"),
                    "db_name": db.get("name"),
                    "exc_type": type(exc).__name__,
                    "exc": _exception_text(exc)[:500],
                    "attempt": attempt + 1,
                    "statement": statement[:800],
                },
                "C",
            )
            # #endregion
            if _is_communication_link_failure(exc) and attempt + 1 < retries:
                continue
            # Do not use `raise ... from exc`: chaining a live pyodbc.Error
            # becomes SystemError: returned a result with an exception set.
            raise ValueError(_sql_error_message(exc))
    if last_exc is not None:
        raise ValueError(_sql_error_message(last_exc))
    rows = []
    for row in fetched:
        if hasattr(row, "keys"):
            rows.append({col: cell_value(row[col]) for col in columns})
        else:
            rows.append({columns[i]: cell_value(row[i]) for i in range(len(columns))})
    return {"sql": statement, "columns": columns, "rows": rows}
