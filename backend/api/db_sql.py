"""SQL Server helpers for docs introspection and db-explorer SELECTs."""

from __future__ import annotations

import re
from typing import Any

from .config_loader import database_to_connection_string, get_database_settings

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FQN_RE = re.compile(
    r"^(?:\[?([A-Za-z_][A-Za-z0-9_]*)\]?\.)?\[?([A-Za-z_][A-Za-z0-9_]*)\]?$"
)
FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|"
    r"xp_|sp_|GRANT|REVOKE|DENY|INTO\s+#|OPENROWSET|OPENDATASOURCE)\b",
    re.IGNORECASE,
)

ALLOWED_LIMITS = {16, 32, 64, 128}


def _require_pyodbc():
    try:
        import pyodbc  # type: ignore
    except ImportError as exc:
        raise ValueError(
            "pyodbc is not installed. Run: pip install pyodbc"
        ) from exc
    return pyodbc


def connect():
    pyodbc = _require_pyodbc()
    db = get_database_settings()
    if not db.get("host") or not db.get("name"):
        raise ValueError("Database host and name must be configured in Settings")
    conn_str = database_to_connection_string(db)
    return pyodbc.connect(conn_str, timeout=15)


def parse_table_name(raw: str) -> tuple[str, str]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("table is required")
    match = FQN_RE.match(text)
    if not match:
        raise ValueError("Invalid table name (use schema.table)")
    schema = match.group(1) or "dbo"
    table = match.group(2)
    if not IDENT_RE.match(schema) or not IDENT_RE.match(table):
        raise ValueError("Invalid schema or table identifier")
    return schema, table


def bracket(ident: str) -> str:
    return f"[{ident}]"


def fqn(schema: str, table: str) -> str:
    return f"{bracket(schema)}.{bracket(table)}"


def validate_where(where: str) -> str:
    clause = (where or "").strip()
    if not clause:
        return ""
    if ";" in clause:
        raise ValueError("WHERE must not contain semicolons")
    if FORBIDDEN_SQL.search(clause):
        raise ValueError("WHERE contains forbidden SQL keywords")
    return clause


def validate_order_column(column: str, columns: list[str] | None = None) -> str:
    col = (column or "").strip()
    if not col:
        return ""
    if not IDENT_RE.match(col):
        raise ValueError("ORDER BY column must be a simple identifier")
    if columns and col not in columns and col.lower() not in {c.lower() for c in columns}:
        raise ValueError(f"Unknown ORDER BY column: {col}")
    return col


def list_tables() -> list[dict[str, Any]]:
    """Introspect user tables and views from INFORMATION_SCHEMA."""
    sql = """
        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    with connect() as conn:
        cur = conn.cursor()
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
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.CHARACTER_MAXIMUM_LENGTH,
            c.IS_NULLABLE,
            c.ORDINAL_POSITION,
            CAST(ep.value AS nvarchar(4000)) AS description
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN sys.schemas s ON s.name = c.TABLE_SCHEMA
        LEFT JOIN sys.objects o ON o.schema_id = s.schema_id AND o.name = c.TABLE_NAME
        LEFT JOIN sys.columns sc
            ON sc.object_id = o.object_id AND sc.name = c.COLUMN_NAME
        LEFT JOIN sys.extended_properties ep
            ON ep.major_id = sc.object_id
            AND ep.minor_id = sc.column_id
            AND ep.name = 'MS_Description'
        WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
        ORDER BY c.ORDINAL_POSITION
    """
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, (schema, table))
        rows = cur.fetchall()
    cols = []
    for name, data_type, max_len, nullable, ordinal, description in rows:
        type_label = str(data_type)
        if max_len is not None and int(max_len) > 0 and int(max_len) < 8000:
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
        SELECT CAST(ep.value AS nvarchar(4000))
        FROM sys.schemas s
        JOIN sys.objects o ON o.schema_id = s.schema_id
        LEFT JOIN sys.extended_properties ep
            ON ep.major_id = o.object_id
            AND ep.minor_id = 0
            AND ep.name = 'MS_Description'
        WHERE s.name = ? AND o.name = ?
    """
    with connect() as conn:
        cur = conn.cursor()
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

    schema, name = parse_table_name(table)
    columns = [c["name"] for c in list_columns(schema, name)]
    if not columns:
        raise ValueError(f"No columns found for {schema}.{name}")

    where_clause = validate_where(where)
    order_col = validate_order_column(order_by, columns)

    # Default ORDER BY first column when needed for TOP/TAIL determinism
    if not order_col:
        order_col = columns[0]

    effective_sort = sort_dir
    if position == "tail":
        # Invert sort so TOP N grabs the end, then reverse in Python for display order
        effective_sort = "DESC" if sort_dir == "ASC" else "ASC"

    select_list = ", ".join(bracket(c) for c in columns)
    target = fqn(schema, name)
    sql = f"SELECT TOP ({int(limit)}) {select_list} FROM {target}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    sql += f" ORDER BY {bracket(order_col)} {effective_sort}"

    with connect() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        raw_rows = cur.fetchall()

    rows = [dict(zip(columns, [(_cell(v)) for v in row])) for row in raw_rows]
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


def _cell(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, (int, float, bool, str)):
        return value
    return str(value)
