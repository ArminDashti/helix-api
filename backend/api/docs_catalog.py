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
                    "description": "",
                }
            )

    merged_columns = []
    doc_cols = doc.get("columns") or {}
    if live_columns:
        for col in live_columns:
            col_name = col["name"]
            md_desc = doc_cols.get(col_name) or doc_cols.get(col_name.lower()) or ""
            sql_description = (col.get("description") or "").strip()
            merged_columns.append(
                {
                    **col,
                    "sql_description": sql_description,
                    "description": md_desc,
                }
            )
    else:
        for col_name, col_desc in doc_cols.items():
            merged_columns.append(
                {
                    "name": col_name,
                    "data_type": "",
                    "nullable": True,
                    "ordinal": 0,
                    "sql_description": "",
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


def _escape_md_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ").strip()


def _upsert_markdown_column(body: str, column: str, description: str) -> str:
    lines = body.splitlines()
    cell_text = _escape_md_cell(description)
    target = column.lower()
    header_idx = None
    last_data_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        if cells[0].lower() == "column":
            header_idx = i
            last_data_idx = i
            continue
        if header_idx is None:
            continue
        last_data_idx = i
        if cells[0].lower() == target:
            rest = cells[2:] if len(cells) > 2 else []
            lines[i] = "| " + " | ".join([cells[0], cell_text, *rest]) + " |"
            joined = "\n".join(lines)
            return joined + ("\n" if body.endswith("\n") else "")
    new_row = f"| {column} | {cell_text} |"
    if last_data_idx is not None:
        lines.insert(last_data_idx + 1, new_row)
        joined = "\n".join(lines)
        return joined + ("\n" if body.endswith("\n") else "")
    prefix = body.rstrip()
    table = f"| Column | Description |\n| --- | --- |\n{new_row}\n"
    if prefix:
        return prefix + "\n\n" + table
    return table


def _ensure_table_section(md: str, heading: str, key: str) -> tuple[str, int, int]:
    matches = list(TABLE_SECTION_RE.finditer(md))
    target_index = None
    for i, match in enumerate(matches):
        title = match.group("title").strip()
        if title.lower() in (key, heading.lower()):
            target_index = i
            break
    if target_index is None:
        md = md.rstrip() + f"\n\n## {heading}\n\n- **Kind:** table\n- **Description:**\n"
        matches = list(TABLE_SECTION_RE.finditer(md))
        target_index = len(matches) - 1
    match = matches[target_index]
    start = match.end()
    end = matches[target_index + 1].start() if target_index + 1 < len(matches) else len(md)
    return md, start, end


def update_column_docs(
    table: str,
    column: str,
    description: str,
    sql_description: str,
) -> dict[str, Any]:
    schema, name = db_sql.parse_table_name(table)
    heading = f"{schema}.{name}"
    key = heading.lower()
    col_name = (column or "").strip()
    if not col_name:
        raise ValueError("column is required")
    md_text = description.strip() if isinstance(description, str) else ""
    sql_text = sql_description.strip() if isinstance(sql_description, str) else ""

    try:
        md = store.get_reference("tables").get("content") or ""
    except FileNotFoundError:
        md = "# Catalog\n\n"
        store.create_reference("tables", md)

    md, start, end = _ensure_table_section(md, heading, key)
    body = md[start:end]
    new_body = _upsert_markdown_column(body, col_name, md_text)
    md = md[:start] + new_body + md[end:]
    store.update_reference("tables", md)

    live_names: set[str] = set()
    try:
        live_names = {c["name"] for c in db_sql.list_columns(schema, name)}
    except Exception:
        live_names = set()
    if col_name in live_names:
        db_sql.set_column_sql_description(schema, name, col_name, sql_text)
    elif sql_text:
        raise ValueError(
            "Cannot write SQL description; column is not in the live schema"
        )
    return get_table_docs(table)
