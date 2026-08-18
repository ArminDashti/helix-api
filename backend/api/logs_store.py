"""Persist failure and error history as JSON under markdown-files."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .markdown_store import root

_LOCK = threading.Lock()
MAX_LOG_ITEMS = 500
VALID_KINDS = frozenset({"pipeline", "llm", "sql", "database", "api"})


def logs_path() -> Path:
    return root() / "logs.json"


def _empty() -> dict[str, Any]:
    return {"items": []}


def _load() -> dict[str, Any]:
    path = logs_path()
    if not path.exists():
        return _empty()
    raw = json.loads(path.read_text(encoding="utf-8") or "{}")
    if not isinstance(raw, dict):
        return _empty()
    items = raw.get("items")
    if not isinstance(items, list):
        return _empty()
    return {"items": items}


def _save(log_file: dict[str, Any]) -> None:
    path = logs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(log_file, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def classify_error_kind(message: str) -> str:
    lowered = (message or "").lower()
    if (
        lowered.startswith("llm ")
        or "llm request" in lowered
        or "llm returned" in lowered
        or "api key is not set" in lowered
        or "base url is not set" in lowered
    ):
        return "llm"
    if any(
        marker in lowered
        for marker in (
            "communication link",
            "login failed",
            "cannot connect",
            "connection refused",
            "odbc",
        )
    ):
        return "database"
    if any(marker in lowered for marker in ("sql", "select", "syntax")):
        return "sql"
    return "pipeline"


def _summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "created_at": item.get("created_at"),
        "kind": item.get("kind") or "pipeline",
        "message": item.get("message") or "",
        "prompt": item.get("prompt") or "",
        "mode": item.get("mode") or "",
    }


def list_logs() -> list[dict[str, Any]]:
    with _LOCK:
        items = _load()["items"]
    summaries = [_summary(item) for item in items if isinstance(item, dict)]
    summaries.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return summaries


def get_log(log_id: str) -> dict[str, Any]:
    with _LOCK:
        for item in _load()["items"]:
            if isinstance(item, dict) and item.get("id") == log_id:
                return item
    raise KeyError(log_id)


def append_error(
    *,
    kind: str,
    message: str,
    prompt: str = "",
    mode: str = "",
    language: str = "",
    agent_id: str = "",
    sql: str = "",
    path: str = "",
    status_code: int | None = None,
) -> dict[str, Any]:
    resolved_kind = kind if kind in VALID_KINDS else classify_error_kind(message)
    item = {
        "id": uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": resolved_kind,
        "message": message or "",
        "prompt": prompt or "",
        "mode": mode or "",
        "language": language or "en",
        "agent_id": agent_id or "",
        "sql": sql or "",
        "path": path or "",
        "status_code": status_code,
    }
    with _LOCK:
        log_file = _load()
        log_file["items"].insert(0, item)
        log_file["items"] = log_file["items"][:MAX_LOG_ITEMS]
        try:
            _save(log_file)
        except OSError:
            pass
    return item


def delete_log(log_id: str) -> None:
    with _LOCK:
        log_file = _load()
        next_items = [
            item
            for item in log_file["items"]
            if not (isinstance(item, dict) and item.get("id") == log_id)
        ]
        if len(next_items) == len(log_file["items"]):
            raise KeyError(log_id)
        log_file["items"] = next_items
        _save(log_file)
