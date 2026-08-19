"""Persist analysis run history as JSON under markdown-files."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .markdown_store import root

_LOCK = threading.Lock()


def results_path() -> Path:
    return root() / "results.json"


def _empty() -> dict[str, Any]:
    return {"items": []}


def _load() -> dict[str, Any]:
    path = results_path()
    if not path.exists():
        return _empty()
    raw = json.loads(path.read_text(encoding="utf-8") or "{}")
    if not isinstance(raw, dict):
        return _empty()
    items = raw.get("items")
    if not isinstance(items, list):
        return _empty()
    return {"items": items}


def _save(data: dict[str, Any]) -> None:
    path = results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _coerce_duration_s(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if value < 0:
            return None
        return round(float(value), 2)
    return None


def _summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "created_at": item.get("created_at"),
        "prompt": item.get("prompt") or "",
        "mode": item.get("mode") or "",
        "language": item.get("language") or "en",
        "archived": bool(item.get("archived")),
        "duration_s": _coerce_duration_s(item.get("duration_s")),
    }


def list_results() -> list[dict[str, Any]]:
    with _LOCK:
        items = _load()["items"]
    summaries = [_summary(item) for item in items if isinstance(item, dict)]
    summaries.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return summaries


def get_result(result_id: str) -> dict[str, Any]:
    with _LOCK:
        for item in _load()["items"]:
            if isinstance(item, dict) and item.get("id") == result_id:
                return item
    raise KeyError(result_id)


def create_result(
    *,
    prompt: str,
    mode: str,
    language: str,
    payload: Any,
    duration_s: Any = None,
) -> dict[str, Any]:
    item = {
        "id": uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "mode": mode,
        "language": language or "en",
        "archived": False,
        "payload": payload,
        "duration_s": _coerce_duration_s(duration_s),
    }
    with _LOCK:
        data = _load()
        data["items"].insert(0, item)
        _save(data)
    return item


def update_result(result_id: str, *, archived: bool) -> dict[str, Any]:
    with _LOCK:
        data = _load()
        found = None
        for item in data["items"]:
            if isinstance(item, dict) and item.get("id") == result_id:
                item["archived"] = bool(archived)
                found = item
                break
        if found is None:
            raise KeyError(result_id)
        _save(data)
        return found


def delete_result(result_id: str) -> None:
    with _LOCK:
        data = _load()
        next_items = [
            item
            for item in data["items"]
            if not (isinstance(item, dict) and item.get("id") == result_id)
        ]
        if len(next_items) == len(data["items"]):
            raise KeyError(result_id)
        data["items"] = next_items
        _save(data)
