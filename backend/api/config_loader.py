"""Read/write helix.config.yaml (database + openrouter sections)."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

DEFAULT_DATABASE = {
    "host": "",
    "port": 1433,
    "name": "",
    "user": "",
    "password": "",
    "driver": "ODBC Driver 18 for SQL Server",
    "trust_server_certificate": True,
    "encrypt": True,
}

DEFAULT_AGENT_MODELS = {
    "task_validator": "openai/gpt-4o-mini",
    "solution_strategist": "anthropic/claude-sonnet-4",
    "technical_architect": "openai/gpt-4o",
    "code_builder": "anthropic/claude-sonnet-4",
    "sql_guardian": "openai/gpt-4o-mini",
    "implementation_auditor": "openai/gpt-4o-mini",
    "response_publisher": "openai/gpt-4o-mini",
}

DEFAULT_OPENROUTER = {
    "site_url": "",
    "app_name": "Helix",
    "default_model": "openai/gpt-4o-mini",
    "agents": {agent_id: {"model": model} for agent_id, model in DEFAULT_AGENT_MODELS.items()},
}


def _config_path() -> Path:
    return Path(settings.HELIX_CONFIG_PATH)


def _example_path() -> Path:
    return Path(settings.HELIX_CONFIG_EXAMPLE_PATH)


def ensure_config_exists() -> Path:
    path = _config_path()
    if path.exists():
        return path
    example = _example_path()
    if example.exists():
        path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        path.write_text(
            yaml.safe_dump({"database": deepcopy(DEFAULT_DATABASE)}, sort_keys=False),
            encoding="utf-8",
        )
    return path


def load_config() -> dict[str, Any]:
    path = ensure_config_exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    return data


def save_config(data: dict[str, Any]) -> None:
    path = ensure_config_exists()
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def get_database_settings() -> dict[str, Any]:
    data = load_config()
    db = data.get("database") or {}
    if not isinstance(db, dict):
        db = {}
    merged = {**DEFAULT_DATABASE, **db}
    # Normalize types
    try:
        merged["port"] = int(merged.get("port") or 1433)
    except (TypeError, ValueError):
        merged["port"] = 1433
    merged["trust_server_certificate"] = bool(merged.get("trust_server_certificate", True))
    merged["encrypt"] = bool(merged.get("encrypt", True))
    for key in ("host", "name", "user", "password", "driver"):
        merged[key] = "" if merged.get(key) is None else str(merged[key])
    return merged


def update_database_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    current = get_database_settings()
    allowed = set(DEFAULT_DATABASE.keys())
    for key, value in payload.items():
        if key not in allowed:
            continue
        if key == "port":
            try:
                current[key] = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("port must be an integer") from exc
        elif key in ("trust_server_certificate", "encrypt"):
            current[key] = bool(value)
        else:
            current[key] = "" if value is None else str(value)
    data["database"] = current
    save_config(data)
    return current


def database_to_connection_string(db: dict[str, Any] | None = None) -> str:
    db = db or get_database_settings()
    parts = [
        f"Driver={{{db['driver']}}}",
        f"Server={db['host']},{db['port']}",
        f"Database={db['name']}",
        f"Uid={db['user']}",
        f"Pwd={db['password']}",
        f"Encrypt={'yes' if db['encrypt'] else 'no'}",
        f"TrustServerCertificate={'yes' if db['trust_server_certificate'] else 'no'}",
    ]
    return ";".join(parts)


def get_openrouter_token() -> str:
    """OpenRouter API token from OPENROUTER_TOKEN only (never from YAML)."""
    return os.environ.get("OPENROUTER_TOKEN", "").strip()


def get_openrouter_settings() -> dict[str, Any]:
    data = load_config()
    raw = data.get("openrouter") or {}
    if not isinstance(raw, dict):
        raw = {}

    agents_raw = raw.get("agents") if isinstance(raw.get("agents"), dict) else {}
    agents: dict[str, dict[str, str]] = {}
    for agent_id, default_model in DEFAULT_AGENT_MODELS.items():
        entry = agents_raw.get(agent_id) if isinstance(agents_raw.get(agent_id), dict) else {}
        model = entry.get("model") if entry else None
        agents[agent_id] = {
            "model": str(model).strip() if model else default_model,
        }

    return {
        "site_url": "" if raw.get("site_url") is None else str(raw.get("site_url")),
        "app_name": (
            DEFAULT_OPENROUTER["app_name"]
            if raw.get("app_name") in (None, "")
            else str(raw.get("app_name"))
        ),
        "default_model": (
            DEFAULT_OPENROUTER["default_model"]
            if not raw.get("default_model")
            else str(raw.get("default_model")).strip()
        ),
        "agents": agents,
        "token_configured": bool(get_openrouter_token()),
    }


def update_openrouter_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    current = get_openrouter_settings()

    if "site_url" in payload:
        current["site_url"] = "" if payload["site_url"] is None else str(payload["site_url"])
    if "app_name" in payload:
        value = payload["app_name"]
        current["app_name"] = (
            DEFAULT_OPENROUTER["app_name"] if value in (None, "") else str(value)
        )
    if "default_model" in payload:
        value = payload["default_model"]
        if value is None or str(value).strip() == "":
            raise ValueError("default_model must be a non-empty string")
        current["default_model"] = str(value).strip()

    agents_payload = payload.get("agents")
    if isinstance(agents_payload, dict):
        for agent_id in DEFAULT_AGENT_MODELS:
            if agent_id not in agents_payload:
                continue
            entry = agents_payload[agent_id]
            if isinstance(entry, dict):
                model = entry.get("model")
            else:
                model = entry
            if model is None or str(model).strip() == "":
                raise ValueError(f"agents.{agent_id}.model must be a non-empty string")
            current["agents"][agent_id] = {"model": str(model).strip()}

    # Persist YAML without the token flag or any api_key
    data["openrouter"] = {
        "site_url": current["site_url"],
        "app_name": current["app_name"],
        "default_model": current["default_model"],
        "agents": deepcopy(current["agents"]),
    }
    save_config(data)
    current["token_configured"] = bool(get_openrouter_token())
    return current
