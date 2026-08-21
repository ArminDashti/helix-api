"""Guardian review of plain-language per-user warehouse data access."""

from __future__ import annotations

import re
from typing import Any

from .llm_client import complete_chat, parse_json_object, require_llm
from .sample_database import SAMPLE_TABLES

_TABLE_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_\.]*")


def _catalog_tables() -> list[str]:
    try:
        from .db_dialects import list_tables

        live = list_tables()
        names = sorted(
            {
                str(item.get("name") or item.get("table") or "").strip()
                for item in (live or [])
                if isinstance(item, dict)
            }
            - {""}
        )
        if names:
            return names
    except Exception:
        pass
    return list(SAMPLE_TABLES)


def _match_tables_from_text(plain: str, catalog: list[str]) -> list[str]:
    lowered = plain.lower()
    found: list[str] = []
    for name in catalog:
        base = name.split(".")[-1]
        if base.lower() in lowered or name.lower() in lowered:
            if name not in found:
                found.append(name)
    return found


def review_data_access_policy(
    plain: str,
    *,
    is_admin: bool = False,
) -> dict[str, Any]:
    """
    Ask the guardian LLM to accept/reject a plain-language data-access policy.

    Returns:
      { "accepted": bool, "message": str, "allowed_tables": list[str],
        "data_access_plain": str }
    """
    cleaned = (plain or "").strip()
    if is_admin and not cleaned:
        return {
            "accepted": True,
            "message": "Admin users have unrestricted SELECT access.",
            "allowed_tables": [],
            "data_access_plain": "",
        }
    if not cleaned:
        return {
            "accepted": False,
            "message": "Data access description is required for non-admin users.",
            "allowed_tables": [],
            "data_access_plain": "",
        }
    if len(cleaned) > 2000:
        return {
            "accepted": False,
            "message": "Data access description must be at most 2000 characters.",
            "allowed_tables": [],
            "data_access_plain": cleaned[:2000],
        }

    catalog = _catalog_tables()
    catalog_blob = ", ".join(catalog[:200])
    system = (
        "You are the Helix guardian agent reviewing a new company user's "
        "warehouse data-access policy written in plain language.\n"
        "Rules:\n"
        "1. Accept only SELECT-only analytics access to named warehouse tables.\n"
        "2. Reject writes, DDL, EXEC, credentials, secrets, or all-tables without limit "
        "for non-admins when the text is vague or dangerous.\n"
        "3. Map the policy to concrete table names from the catalog when possible.\n"
        "4. Reply with JSON only: "
        '{"result":"done"|"fail","message":"...","allowed_tables":["Table",...]}\n'
        "5. On done, allowed_tables must be a non-empty subset of the catalog "
        "(use exact catalog names)."
    )
    user = (
        f"Plain-language policy:\n{cleaned}\n\n"
        f"Catalog tables:\n{catalog_blob}\n\n"
        f"Caller is_admin={is_admin}."
    )

    try:
        require_llm()
        raw = complete_chat("guardian", user, system)
        parsed = parse_json_object(raw)
    except Exception as exc:
        # Fail closed for non-admins when guardian cannot run.
        heuristic = _match_tables_from_text(cleaned, catalog)
        if heuristic and not any(
            bad in cleaned.lower()
            for bad in ("all tables", "everything", "drop", "delete", "insert", "password", "api key")
        ):
            return {
                "accepted": True,
                "message": f"Guardian unavailable ({exc}); accepted via table-name match.",
                "allowed_tables": heuristic,
                "data_access_plain": cleaned,
            }
        return {
            "accepted": False,
            "message": f"Guardian could not review access policy: {exc}",
            "allowed_tables": [],
            "data_access_plain": cleaned,
        }

    result = str(parsed.get("result") or "").strip().lower()
    message = str(parsed.get("message") or "").strip() or "Guardian rejected the access policy."
    raw_tables = parsed.get("allowed_tables")
    allowed: list[str] = []
    catalog_lower = {name.lower(): name for name in catalog}
    if isinstance(raw_tables, list):
        for item in raw_tables:
            token = str(item or "").strip()
            if not token:
                continue
            match = catalog_lower.get(token.lower()) or catalog_lower.get(
                token.split(".")[-1].lower()
            )
            if match and match not in allowed:
                allowed.append(match)
    if not allowed:
        allowed = _match_tables_from_text(cleaned, catalog)

    if result in ("done", "pass", "ok", "accepted", "allow"):
        if not is_admin and not allowed:
            return {
                "accepted": False,
                "message": message
                or "Guardian accepted but could not map any catalog tables.",
                "allowed_tables": [],
                "data_access_plain": cleaned,
            }
        return {
            "accepted": True,
            "message": message or "Access policy accepted.",
            "allowed_tables": allowed if not is_admin else allowed,
            "data_access_plain": cleaned,
        }

    return {
        "accepted": False,
        "message": message,
        "allowed_tables": [],
        "data_access_plain": cleaned,
    }
