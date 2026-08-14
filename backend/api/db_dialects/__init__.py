"""Database engine dispatch for analytics SQL operations."""

from __future__ import annotations

from typing import Any

from ..config_loader import get_database_engine
from . import postgresql, sqlite, sqlserver
from .base import ALLOWED_LIMITS, normalize_engine, parse_table_name

_DIALECTS = {
    "postgresql": postgresql,
    "sqlserver": sqlserver,
    "sqlite": sqlite,
}


def get_dialect():
    return _DIALECTS[get_database_engine()]


def connect():
    return get_dialect().connect()


def list_tables() -> list[dict[str, Any]]:
    return get_dialect().list_tables()


def list_columns(schema: str, table: str) -> list[dict[str, Any]]:
    return get_dialect().list_columns(schema, table)


def table_overview(schema: str, table: str) -> dict[str, Any]:
    return get_dialect().table_overview(schema, table)


def select_rows(**kwargs) -> dict[str, Any]:
    return get_dialect().select_rows(**kwargs)


def parse_table_name_for_engine(raw: str) -> tuple[str, str]:
    dialect = get_dialect()
    default_schema = dialect.default_schema()
    return parse_table_name(raw, default_schema=default_schema)


__all__ = [
    "ALLOWED_LIMITS",
    "connect",
    "list_columns",
    "list_tables",
    "normalize_engine",
    "parse_table_name_for_engine",
    "select_rows",
    "table_overview",
]
