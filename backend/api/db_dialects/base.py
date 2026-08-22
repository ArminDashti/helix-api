"""Shared SQL introspection helpers for all database engines."""

from __future__ import annotations

import re
from typing import Any

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

ENGINE_ALIASES = {
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "pg": "postgresql",
    "sqlserver": "sqlserver",
    "mssql": "sqlserver",
    "sqlite": "sqlite",
}


def normalize_engine(raw: str | None) -> str:
    if raw is None or not str(raw).strip():
        return "sqlite"
    key = str(raw).strip().lower()
    return ENGINE_ALIASES.get(key, "postgresql")


def parse_table_name(raw: str, *, default_schema: str) -> tuple[str, str]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("table is required")
    match = FQN_RE.match(text)
    if not match:
        raise ValueError("Invalid table name (use schema.table)")
    schema = match.group(1) or default_schema
    table = match.group(2)
    if not IDENT_RE.match(schema) or not IDENT_RE.match(table):
        raise ValueError("Invalid schema or table identifier")
    return schema, table


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


def _looks_like_id_column(name: str) -> bool:
    text = (name or "").strip()
    if not text:
        return False
    lower = text.lower()
    if lower == "id":
        return True
    if lower.endswith("_id"):
        return True
    if len(text) > 2 and text.endswith(("Id", "ID")):
        return True
    return False


def prefer_id_order_column(
    columns: list[Any],
) -> str:
    """Pick a default ORDER BY column: PK, then *Id / id, then lowest ordinal."""
    if not columns:
        return ""

    metas: list[dict[str, Any]] = []
    for item in columns:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            metas.append(
                {
                    "name": name,
                    "description": str(item.get("description") or ""),
                    "ordinal": item.get("ordinal"),
                }
            )
        else:
            name = str(item or "").strip()
            if name:
                metas.append({"name": name, "description": "", "ordinal": None})

    if not metas:
        return ""

    for meta in metas:
        if meta["description"].strip().upper() == "PRIMARY KEY":
            return meta["name"]

    for meta in metas:
        if _looks_like_id_column(meta["name"]):
            return meta["name"]

    with_ordinal = [m for m in metas if isinstance(m.get("ordinal"), (int, float))]
    if with_ordinal:
        with_ordinal.sort(key=lambda m: int(m["ordinal"]))
        return with_ordinal[0]["name"]

    return metas[0]["name"]


def cell_value(value: Any) -> Any:
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
