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

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LIMIT = re.compile(r"\b(LIMIT|TOP|FETCH)\b", re.IGNORECASE)
_STAR = re.compile(r"SELECT\s+\*", re.IGNORECASE)
_WITH = re.compile(r"^\s*WITH\b", re.IGNORECASE)
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
        list_error = f"{type(exc).__name__}: {exc}"
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


def validate_select(sql: str) -> str:
    settings = get_sql_settings()
    statement = extract_sql(sql)
    statement = _rewrite_saleslt_to_pakhsh(statement)
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
    allowed = _allowlisted_names()
    skip = {
        "select",
        "from",
        "where",
        "and",
        "or",
        "join",
        "left",
        "right",
        "inner",
        "outer",
        "on",
        "as",
        "group",
        "by",
        "order",
        "limit",
        "top",
        "fetch",
        "with",
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "distinct",
        "case",
        "when",
        "then",
        "else",
        "end",
        "null",
        "not",
        "in",
        "is",
        "like",
        "between",
        "having",
        "union",
        "all",
        "asc",
        "desc",
        "offset",
        "rows",
        "only",
        "saleslt",
        "main",
        "dbo",
    }
    for ident in _IDENT.findall(statement):
        lower = ident.lower()
        if lower in skip or lower.startswith("col"):
            continue
        if ident[:1].isupper() or ident in SAMPLE_TABLES:
            if lower not in allowed and ident not in SAMPLE_TABLES:
                # Column names are allowed; only flag known table-like tokens
                # that are not in the allowlist when they appear after FROM/JOIN.
                continue
    from_tokens = re.findall(
        r"\b(?:FROM|JOIN)\s+(?:\[?([A-Za-z_][A-Za-z0-9_]*)\]?\.)?\[?([A-Za-z_][A-Za-z0-9_]*)\]?",
        statement,
        re.IGNORECASE,
    )
    # #region agent log
    _dbg(
        "sql_execute.py:validate_select",
        "FROM/JOIN tokens vs allowlist",
        {
            "from_tokens": [{"schema": schema, "table": table} for schema, table in from_tokens],
            "allowed_contains_tables": {
                table.lower(): table.lower() in allowed for _, table in from_tokens
            },
            "sql_preview": statement[:500],
        },
        "A",
    )
    # #endregion
    for schema, table in from_tokens:
        if table.lower() not in allowed:
            raise ValueError(f"Table {table} is not on the allowlist")
        _ = schema
    max_rows = int(settings["max_rows"])
    if not _LIMIT.search(statement):
        statement = f"{statement} LIMIT {max_rows}"
    return statement


def execute_select(sql: str) -> dict[str, Any]:
    statement = validate_select(sql)
    settings = get_sql_settings()
    max_rows = int(settings["max_rows"])
    db = get_database_settings()
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
    try:
        with connect() as conn:
            cur = conn.cursor()
            cur.execute(statement)
            desc = cur.description or []
            columns = [str(col[0]) for col in desc]
            fetched = cur.fetchmany(max_rows)
    except Exception as exc:
        # #region agent log
        _dbg(
            "sql_execute.py:execute_select",
            "execute failed",
            {
                "engine": db.get("engine"),
                "db_name": db.get("name"),
                "exc_type": type(exc).__name__,
                "exc": str(exc)[:500],
                "statement": statement[:800],
            },
            "C",
        )
        # #endregion
        raise
    rows = []
    for row in fetched:
        if hasattr(row, "keys"):
            rows.append({col: cell_value(row[col]) for col in columns})
        else:
            rows.append({columns[i]: cell_value(row[i]) for i in range(len(columns))})
    return {"sql": statement, "columns": columns, "rows": rows}
