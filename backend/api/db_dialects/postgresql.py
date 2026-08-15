"""PostgreSQL dialect for docs introspection and db-explorer SELECTs."""

from __future__ import annotations

from typing import Any

from ..config_loader import database_to_connection_string, get_database_settings
from .base import (
    ALLOWED_LIMITS,
    cell_value,
    parse_table_name,
    validate_order_column,
    validate_where,
)


def _require_psycopg():
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise ValueError(
            "psycopg is not installed. Run: pip install 'psycopg[binary]'"
        ) from exc
    return psycopg


def connect():
    psycopg = _require_psycopg()
    db = get_database_settings()
    if not db.get("host") or not db.get("name"):
        raise ValueError("Database host and name must be configured in Settings")
    conn_str = database_to_connection_string(db)
    return psycopg.connect(conn_str, connect_timeout=15)


def default_schema() -> str:
    return "public"


def quote_ident(ident: str) -> str:
    return f'"{ident}"'


def fqn(schema: str, table: str) -> str:
    return f"{quote_ident(schema)}.{quote_ident(table)}"


def list_tables() -> list[dict[str, Any]]:
    sql = """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
          AND table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY table_schema, table_name
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    result = []
    for schema, name, kind in rows:
        result.append(
            {
                "schema": schema,
                "name": name,
                "full_name": f"{schema}.{name}",
                "kind": "view" if str(kind).upper() == "VIEW" else "table",
            }
        )
    return result


def list_columns(schema: str, table: str) -> list[dict[str, Any]]:
    sql = """
        SELECT
            c.column_name,
            c.data_type,
            c.character_maximum_length,
            c.is_nullable,
            c.ordinal_position,
            pg_catalog.col_description(
                (quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass,
                c.ordinal_position
            ) AS description
        FROM information_schema.columns c
        WHERE c.table_schema = %s AND c.table_name = %s
        ORDER BY c.ordinal_position
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (schema, table))
            rows = cur.fetchall()
    cols = []
    for name, data_type, max_len, nullable, ordinal, description in rows:
        type_label = str(data_type)
        if max_len is not None and int(max_len) > 0:
            type_label = f"{data_type}({max_len})"
        cols.append(
            {
                "name": name,
                "data_type": type_label,
                "nullable": str(nullable).upper() == "YES",
                "ordinal": int(ordinal),
                "description": (description or "").strip(),
            }
        )
    return cols


def table_overview(schema: str, table: str) -> dict[str, Any]:
    sql = """
        SELECT obj_description(
            (quote_ident(%s) || '.' || quote_ident(%s))::regclass,
            'pg_class'
        )
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (schema, table))
            row = cur.fetchone()
    overview = (row[0] if row and row[0] else "") or ""
    return {
        "schema": schema,
        "name": table,
        "full_name": f"{schema}.{table}",
        "overview": overview.strip(),
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
    columns = [c["name"] for c in list_columns(schema, name)]
    if not columns:
        raise ValueError(f"No columns found for {schema}.{name}")

    where_clause = validate_where(where)
    order_col = validate_order_column(order_by, columns)
    if not order_col:
        order_col = columns[0]

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
        with conn.cursor() as cur:
            cur.execute(sql)
            raw_rows = cur.fetchall()

    rows = [dict(zip(columns, [cell_value(v) for v in row])) for row in raw_rows]
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
    names = {c["name"] for c in list_columns(schema, table)}
    if column not in names:
        raise ValueError(f"Unknown column {column}")
    target = f"{fqn(schema, table)}.{quote_ident(column)}"
    text = (description or "").strip() or None
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"COMMENT ON COLUMN {target} IS %s", (text,))
        conn.commit()

