"""Multi-engine SQL helpers for docs introspection and db-explorer SELECTs."""

from __future__ import annotations

from typing import Any

from .db_dialects import (
    ALLOWED_LIMITS,
    connect,
    list_columns,
    list_tables,
    parse_table_name_for_engine,
    select_rows,
    set_column_sql_description,
    table_overview,
)
from .db_dialects.base import parse_table_name as _parse_table_name


def parse_table_name(raw: str) -> tuple[str, str]:
    return parse_table_name_for_engine(raw)


__all__ = [
    "ALLOWED_LIMITS",
    "connect",
    "list_columns",
    "list_tables",
    "parse_table_name",
    "select_rows",
    "set_column_sql_description",
    "table_overview",
]
