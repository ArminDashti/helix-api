"""SQLite dialect for docs introspection and db-explorer SELECTs."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..config_loader import get_database_settings
from ..sample_database import SAMPLE_SCHEMA, resolve_sqlite_path
from .base import (
    ALLOWED_LIMITS,
    cell_value,
    parse_table_name,
    prefer_id_order_column,
    validate_order_column,
    validate_where,
)

# Schemas that map to the main SQLite catalog (sample DB uses SalesLT.* naming).
_LOCAL_SCHEMAS = {"main", SAMPLE_SCHEMA.lower(), "dbo", "sales"}


def connect():
    from ..sample_database import ensure_sqlite_file

    db = get_database_settings()
    path = resolve_sqlite_path(db.get("name") or db.get("path") or "")
    if not path:
        raise ValueError("SQLite database file path must be configured in Settings")
    ensure_sqlite_file(path)
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def default_schema() -> str:
    return SAMPLE_SCHEMA


def quote_ident(ident: str) -> str:
    return f'"{ident}"'


def fqn(schema: str, table: str) -> str:
    if (schema or "").lower() in _LOCAL_SCHEMAS or not schema:
        return quote_ident(table)
    return f"{quote_ident(schema)}.{quote_ident(table)}"


def list_tables() -> list[dict[str, Any]]:
    sql = """
        SELECT name, type
        FROM sqlite_master
        WHERE type IN ('table', 'view')
          AND name NOT LIKE 'sqlite_%'
          AND name NOT LIKE '\\_%' ESCAPE '\\'
        ORDER BY name
    """
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
    schema = default_schema()
    return [
        {
            "schema": schema,
            "name": name,
            "full_name": f"{schema}.{name}",
            "kind": "view" if str(kind).lower() == "view" else "table",
        }
        for name, kind in rows
    ]


def list_columns(schema: str, table: str) -> list[dict[str, Any]]:
    del schema  # Sample/local SQLite tables live in the main catalog
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({quote_ident(table)})")
        rows = cur.fetchall()
    cols = []
    for row in rows:
        cid, name, col_type, notnull, _default, pk = row
        cols.append(
            {
                "name": name,
                "data_type": col_type or "TEXT",
                "nullable": not notnull,
                "ordinal": int(cid) + 1,
                "description": "PRIMARY KEY" if pk else "",
            }
        )
    return cols


def table_overview(schema: str, table: str) -> dict[str, Any]:
    resolved = schema or default_schema()
    return {
        "schema": resolved,
        "name": table,
        "full_name": f"{resolved}.{table}",
        "overview": "",
        "columns": list_columns(schema, table),
    }


def select_rows(
    *,
    table: str,
    limit: int = 32,
    position: str = "top",
    where: str = "",
    order_by: str = "",
    sort: str = "ASC",
) -> dict[str, Any]:
    if limit not in ALLOWED_LIMITS:
        raise ValueError("limit must be one of 16, 32, 64, 128")
    position = (position or "top").lower().strip()
    if position not in ("top", "tail"):
        raise ValueError("position must be top or tail")
    sort_dir = (sort or "ASC").upper().strip()
    if sort_dir not in ("ASC", "DESC"):
        raise ValueError("sort must be ASC or DESC")

    schema, name = parse_table_name(table, default_schema=default_schema())
    col_metas = list_columns(schema, name)
    columns = [c["name"] for c in col_metas]
    if not columns:
        raise ValueError(f"No columns found for {schema}.{name}")

    where_clause = validate_where(where)
    order_col = validate_order_column(order_by, columns)
    if not order_col:
        order_col = prefer_id_order_column(col_metas) or columns[0]

    effective_sort = sort_dir
    if position == "tail":
        effective_sort = "DESC" if sort_dir == "ASC" else "ASC"

    select_list = ", ".join(quote_ident(c) for c in columns)
    target = fqn(schema, name)
    sql = f"SELECT {select_list} FROM {target}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    sql += f" ORDER BY {quote_ident(order_col)} {effective_sort} LIMIT {int(limit)}"

    with connect() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        raw_rows = cur.fetchall()

    rows = [
        dict(zip(columns, [cell_value(row[c]) for c in columns]))
        for row in raw_rows
    ]
    if position == "tail":
        rows.reverse()

    return {
        "table": f"{schema}.{name}",
        "limit": limit,
        "position": position,
        "where": where_clause,
        "order_by": order_col,
        "sort": sort_dir,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


def set_column_sql_description(
    schema: str, table: str, column: str, description: str
) -> None:
    del schema, table, column
    if (description or "").strip():
        raise ValueError("SQLite does not store column SQL descriptions")

