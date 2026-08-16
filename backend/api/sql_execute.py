"""Validate and execute SELECT statements for the SQL agent."""

from __future__ import annotations

import re
from typing import Any

from .config_loader import get_sql_settings
from .db_dialects import connect, list_tables
from .db_dialects.base import FORBIDDEN_SQL, cell_value
from .sample_database import SAMPLE_TABLES

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LIMIT = re.compile(r"\b(LIMIT|TOP|FETCH)\b", re.IGNORECASE)
_STAR = re.compile(r"SELECT\s+\*", re.IGNORECASE)
_WITH = re.compile(r"^\s*WITH\b", re.IGNORECASE)
_SELECT = re.compile(r"^\s*(WITH\b[\s\S]+?\bSELECT\b|SELECT\b)", re.IGNORECASE)


def extract_sql(text: str) -> str:
    raw = (text or "").strip()
    fence = re.search(r"```(?:sql)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    if raw.lower().startswith("sql:"):
        raw = raw[4:].strip()
    return raw.rstrip(";").strip()


def _allowlisted_names() -> set[str]:
    names = {t.lower() for t in SAMPLE_TABLES}
    try:
        for table in list_tables():
            names.add(str(table.get("name") or "").lower())
    except Exception:
        pass
    names.discard("")
    return names


def validate_select(sql: str) -> str:
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
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(statement)
        desc = cur.description or []
        columns = [str(col[0]) for col in desc]
        fetched = cur.fetchmany(max_rows)
    rows = []
    for row in fetched:
        if hasattr(row, "keys"):
            rows.append({col: cell_value(row[col]) for col in columns})
        else:
            rows.append({columns[i]: cell_value(row[i]) for i in range(len(columns))})
    return {"sql": statement, "columns": columns, "rows": rows}
