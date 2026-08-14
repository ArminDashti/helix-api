"""Docs: merge SQL Server introspection with markdown table documentation."""

from __future__ import annotations

import re
from typing import Any

from . import db_sql
from . import markdown_store as store

TABLE_SECTION_RE = re.compile(
    r"^##\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)


def _docs_markdown() -> str:
    try:
        ref = store.get_reference("tables")
        return ref.get("content") or ""
    except FileNotFoundError:
        return ""


def _parse_docs_sections(md: str) -> dict[str, dict[str, Any]]:
    """Parse ## schema.table sections with overview + column table."""
    sections: dict[str, dict[str, Any]] = {}
    if not md.strip():
        return sections

    matches = list(TABLE_SECTION_RE.finditer(md))
    for i, match in enumerate(matches):
        title = match.group("title").strip()
        if title.lower() in ("allowed objects", "catalog"):
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[start:end].strip()
        overview = ""
        columns: dict[str, str] = {}
        kind = ""
        for line in body.splitlines():
            stripped = line.strip()
            low = stripped.lower()
            if low.startswith("- **kind:**") or low.startswith("- **kind**:"):
                kind = stripped.split(":", 1)[-1].strip().strip("*").strip()
            elif low.startswith("- **description:**") or low.startswith(
                "- **description**:"
            ):
                overview = stripped.split(":", 1)[-1].strip().strip("*").strip()
            elif stripped.startswith("|") and "---" not in stripped:
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cells) >= 2 and cells[0].lower() != "column":
                    columns[cells[0]] = cells[1]
        try:
            schema, name = db_sql.parse_table_name(title)
            key = f"{schema}.{name}".lower()
        except ValueError:
            key = title.lower()
            schema, name = "", title
        sections[key] = {
            "schema": schema,
            "name": name,
            "full_name": f"{schema}.{name}" if schema else title,
            "overview": overview,
            "kind": kind,
            "columns": columns,
        }
    return sections


def list_docs_tables() -> dict[str, Any]:
    docs = _parse_docs_sections(_docs_markdown())
    live: list[dict[str, Any]] = []
    source = "markdown"
    error = None
    try:
        live = db_sql.list_tables()
        source = "database"
    except Exception as exc:  # noqa: BLE001 — surface to UI
        error = str(exc)
        # Fall back to documented tables only
        for section in docs.values():
            live.append(
                {
                    "schema": section.get("schema") or "dbo",
                    "name": section.get("name") or section.get("full_name"),
                    "full_name": section.get("full_name"),
                    "kind": section.get("kind") or "table",
                }
            )
        source = "markdown" if live else "none"

    tables = []
    for item in live:
        key = str(item.get("full_name", "")).lower()
        doc = docs.get(key) or {}
        tables.append(
            {
                **item,
                "has_docs": bool(doc),
                "overview_preview": (doc.get("overview") or "")[:160],
            }
        )
    return {"tables": tables, "source": source, "error": error}


def get_table_docs(table: str) -> dict[str, Any]:
    schema, name = db_sql.parse_table_name(table)
    docs = _parse_docs_sections(_docs_markdown())
    key = f"{schema}.{name}".lower()
    doc = docs.get(key) or {}

    live_overview = ""
    live_columns: list[dict[str, Any]] = []
    source = "markdown"
    error = None
    try:
        overview_payload = db_sql.table_overview(schema, name)
        live_overview = overview_payload.get("overview") or ""
        live_columns = overview_payload.get("columns") or []
        source = "database"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        # Build columns from markdown only
        for col_name, col_desc in (doc.get("columns") or {}).items():
            live_columns.append(
                {
                    "name": col_name,
                    "data_type": "",
                    "nullable": True,
                    "ordinal": 0,
                    "description": col_desc,
                }
            )

    merged_columns = []
    doc_cols = doc.get("columns") or {}
    if live_columns:
        for col in live_columns:
            col_name = col["name"]
            md_desc = doc_cols.get(col_name) or doc_cols.get(col_name.lower()) or ""
            description = (col.get("description") or "").strip() or md_desc
            merged_columns.append({**col, "description": description})
    else:
        for col_name, col_desc in doc_cols.items():
            merged_columns.append(
                {
                    "name": col_name,
                    "data_type": "",
                    "nullable": True,
                    "ordinal": 0,
                    "description": col_desc,
                }
            )

    overview = (doc.get("overview") or "").strip() or live_overview
    return {
        "schema": schema,
        "name": name,
        "full_name": f"{schema}.{name}",
        "kind": doc.get("kind") or "",
        "overview": overview,
        "columns": merged_columns,
        "source": source,
        "error": error,
    }


def update_table_overview(table: str, overview: str) -> dict[str, Any]:
    """Write the table explanation into references/tables.md and return merged docs."""
    schema, name = db_sql.parse_table_name(table)
    heading = f"{schema}.{name}"
    key = heading.lower()
    text = overview.strip() if isinstance(overview, str) else ""
    desc_line = f"- **Description:** {text}" if text else "- **Description:**"

    try:
        md = store.get_reference("tables").get("content") or ""
    except FileNotFoundError:
        md = "# Catalog\n\n"
        store.create_reference("tables", md)

    matches = list(TABLE_SECTION_RE.finditer(md))
    target_index = None
    for i, match in enumerate(matches):
        title = match.group("title").strip()
        if title.lower() in (key, heading.lower()):
            target_index = i
            break

    if target_index is None:
        block = f"\n## {heading}\n\n- **Kind:** table\n{desc_line}\n"
        md = md.rstrip() + "\n" + block
    else:
        match = matches[target_index]
        start = match.end()
        end = (
            matches[target_index + 1].start()
            if target_index + 1 < len(matches)
            else len(md)
        )
        body = md[start:end]
        new_body, n = re.subn(
            r"(?im)^-\s+\*\*Description:?\*\*:?[^\n]*",
            desc_line,
            body,
            count=1,
        )
        if n == 0:
            kind_m = re.search(r"(?im)^-\s+\*\*Kind:?\*\*:?[^\n]*\n?", body)
            if kind_m:
                new_body = (
                    body[: kind_m.end()] + desc_line + "\n" + body[kind_m.end() :]
                )
            else:
                new_body = "\n" + desc_line + "\n" + body.lstrip("\n")
        md = md[:start] + new_body + md[end:]

    store.update_reference("tables", md)
    return get_table_docs(table)
