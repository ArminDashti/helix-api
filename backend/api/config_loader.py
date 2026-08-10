"""Read/write helix.config.yaml (database + openrouter + cursor sections)."""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

from .agents import AGENT_BY_ID, AGENT_PIPELINE, is_builtin_agent

AGENT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

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

DEFAULT_CURSOR_AGENT_MODELS = {
    "task_validator": "composer-2",
    "solution_strategist": "composer-2",
    "technical_architect": "composer-2",
    "code_builder": "composer-2",
    "sql_guardian": "composer-2",
    "implementation_auditor": "composer-2",
    "response_publisher": "composer-2",
}

DEFAULT_OPENROUTER = {
    "site_url": "",
    "app_name": "Helix",
    "default_model": "openai/gpt-4o-mini",
    "agents": {agent_id: {"model": model} for agent_id, model in DEFAULT_AGENT_MODELS.items()},
}

DEFAULT_CURSOR = {
    "app_name": "Helix",
    "default_model": "composer-2",
    "agents": {
        agent_id: {"model": model} for agent_id, model in DEFAULT_CURSOR_AGENT_MODELS.items()
    },
}

DEFAULT_PROVIDER = "openrouter"


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


_MODELS_CACHE: dict[str, Any] = {"fetched_at": 0.0, "models": []}
_MODELS_CACHE_TTL_SEC = 600


def fetch_openrouter_models(*, force: bool = False) -> list[dict[str, str]]:
    """
    Fetch OpenRouter model catalog (cached ~10 minutes).
    Returns list of {id, name}. Raises ValueError if token missing or request fails.
    """
    now = time.time()
    if (
        not force
        and _MODELS_CACHE["models"]
        and (now - float(_MODELS_CACHE["fetched_at"])) < _MODELS_CACHE_TTL_SEC
    ):
        return list(_MODELS_CACHE["models"])

    token = get_openrouter_token()
    if not token:
        raise ValueError("OPENROUTER_TOKEN is not set")

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise ValueError(f"OpenRouter models request failed ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"OpenRouter models request failed: {exc.reason}") from exc

    raw_list = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(raw_list, list):
        raise ValueError("Unexpected OpenRouter models response")

    models: list[dict[str, str]] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not model_id:
            continue
        name = item.get("name") or model_id
        models.append({"id": str(model_id), "name": str(name)})

    models.sort(key=lambda m: m["id"].lower())
    _MODELS_CACHE["fetched_at"] = now
    _MODELS_CACHE["models"] = models
    return list(models)


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
    # Optional model overrides for custom agents (fall back to default_model at runtime)
    default_model = (
        DEFAULT_OPENROUTER["default_model"]
        if not raw.get("default_model")
        else str(raw.get("default_model")).strip()
    )
    for meta in get_custom_agents():
        agent_id = meta["id"]
        entry = agents_raw.get(agent_id) if isinstance(agents_raw.get(agent_id), dict) else {}
        model = entry.get("model") if entry else None
        if model and str(model).strip():
            agents[agent_id] = {"model": str(model).strip()}
        elif agent_id in agents_raw:
            agents[agent_id] = {"model": default_model}

    return {
        "site_url": "" if raw.get("site_url") is None else str(raw.get("site_url")),
        "app_name": (
            DEFAULT_OPENROUTER["app_name"]
            if raw.get("app_name") in (None, "")
            else str(raw.get("app_name"))
        ),
        "default_model": default_model,
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
        allowed_ids = known_agent_ids()
        for agent_id, entry in agents_payload.items():
            agent_key = str(agent_id)
            if agent_key not in allowed_ids:
                continue
            if isinstance(entry, dict):
                model = entry.get("model")
            else:
                model = entry
            if model is None or str(model).strip() == "":
                raise ValueError(f"agents.{agent_key}.model must be a non-empty string")
            current["agents"][agent_key] = {"model": str(model).strip()}

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


def get_provider() -> str:
    data = load_config()
    raw = data.get("provider")
    if isinstance(raw, str) and raw.strip().lower() in ("openrouter", "cursor"):
        return raw.strip().lower()
    return DEFAULT_PROVIDER


def update_provider(provider: str) -> str:
    value = (provider or "").strip().lower()
    if value not in ("openrouter", "cursor"):
        raise ValueError("provider must be openrouter or cursor")
    data = load_config()
    data["provider"] = value
    save_config(data)
    return value


def get_custom_agents() -> list[dict[str, str]]:
    data = load_config()
    raw = data.get("custom_agents")
    if not isinstance(raw, list):
        return []
    agents: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        agent_id = str(entry.get("id") or "").strip()
        if not agent_id or agent_id in seen or agent_id in AGENT_BY_ID:
            continue
        if not AGENT_ID_RE.match(agent_id):
            continue
        seen.add(agent_id)
        name = str(entry.get("name") or "").strip() or agent_id
        description = str(entry.get("description") or "").strip()
        agents.append(
            {
                "id": agent_id,
                "name": name,
                "description": description,
                "builtin": False,
            }
        )
    return agents


def get_all_agent_metas() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for meta in AGENT_PIPELINE:
        result.append({**meta, "builtin": True})
    result.extend(get_custom_agents())
    return result


def known_agent_ids() -> set[str]:
    return {meta["id"] for meta in get_all_agent_metas()}


def get_agent_meta(agent_id: str) -> dict[str, Any]:
    for meta in get_all_agent_metas():
        if meta["id"] == agent_id:
            return dict(meta)
    raise KeyError(f"Unknown agent: {agent_id}")


def create_custom_agent(
    agent_id: str,
    name: str,
    description: str = "",
    *,
    instruction: str = "",
) -> dict[str, Any]:
    cleaned_id = (agent_id or "").strip()
    if not AGENT_ID_RE.match(cleaned_id):
        raise ValueError(
            "id must be lowercase letters, digits, or underscores, starting with a letter"
        )
    if cleaned_id in known_agent_ids():
        raise ValueError(f"Agent already exists: {cleaned_id}")
    cleaned_name = (name or "").strip()
    if not cleaned_name:
        raise ValueError("name must be a non-empty string")
    if len(cleaned_name) > 80:
        raise ValueError("name must be at most 80 characters")
    cleaned_description = (description or "").strip()
    if len(cleaned_description) > 500:
        raise ValueError("description must be at most 500 characters")

    data = load_config()
    custom = data.get("custom_agents")
    if not isinstance(custom, list):
        custom = []
    custom.append(
        {
            "id": cleaned_id,
            "name": cleaned_name,
            "description": cleaned_description,
        }
    )
    data["custom_agents"] = custom
    save_config(data)

    # Lazy import avoids circular import at module load
    from . import markdown_store as store

    store.ensure_dirs()
    instr_path = store.instructions_dir() / f"{cleaned_id}.md"
    if not instr_path.exists():
        instr_path.write_text(
            instruction if isinstance(instruction, str) else "",
            encoding="utf-8",
        )
    skills_path = store.skills_dir() / cleaned_id
    skills_path.mkdir(parents=True, exist_ok=True)

    return {
        "id": cleaned_id,
        "name": cleaned_name,
        "description": cleaned_description,
        "builtin": False,
        "instruction": instr_path.read_text(encoding="utf-8") if instr_path.exists() else "",
    }


def delete_custom_agent(agent_id: str) -> None:
    cleaned_id = (agent_id or "").strip()
    if is_builtin_agent(cleaned_id):
        raise ValueError("Cannot delete a built-in pipeline agent")
    data = load_config()
    custom = data.get("custom_agents")
    if not isinstance(custom, list):
        raise KeyError(f"Unknown agent: {cleaned_id}")
    next_custom = [
        entry
        for entry in custom
        if isinstance(entry, dict) and str(entry.get("id") or "").strip() != cleaned_id
    ]
    if len(next_custom) == len(custom):
        raise KeyError(f"Unknown agent: {cleaned_id}")
    data["custom_agents"] = next_custom

    names = data.get("agent_names") if isinstance(data.get("agent_names"), dict) else {}
    if cleaned_id in names:
        names = dict(names)
        names.pop(cleaned_id, None)
        data["agent_names"] = names

    for section in ("openrouter", "cursor"):
        section_data = data.get(section)
        if isinstance(section_data, dict) and isinstance(section_data.get("agents"), dict):
            agents = dict(section_data["agents"])
            agents.pop(cleaned_id, None)
            section_data = dict(section_data)
            section_data["agents"] = agents
            data[section] = section_data

    save_config(data)

    from . import markdown_store as store

    instr_path = store.instructions_dir() / f"{cleaned_id}.md"
    if instr_path.exists():
        instr_path.unlink()


def get_agent_display_names() -> dict[str, str]:
    data = load_config()
    raw = data.get("agent_names") if isinstance(data.get("agent_names"), dict) else {}
    names: dict[str, str] = {}
    for meta in get_all_agent_metas():
        override = raw.get(meta["id"])
        names[meta["id"]] = (
            str(override).strip() if override and str(override).strip() else meta["name"]
        )
    return names


def update_agent_display_name(agent_id: str, name: str) -> dict[str, str]:
    if agent_id not in known_agent_ids():
        raise KeyError(f"Unknown agent: {agent_id}")
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("name must be a non-empty string")
    if len(cleaned) > 80:
        raise ValueError("name must be at most 80 characters")
    data = load_config()
    if not is_builtin_agent(agent_id):
        custom = data.get("custom_agents")
        if isinstance(custom, list):
            for entry in custom:
                if isinstance(entry, dict) and str(entry.get("id") or "").strip() == agent_id:
                    entry["name"] = cleaned
                    break
    names = data.get("agent_names") if isinstance(data.get("agent_names"), dict) else {}
    names[agent_id] = cleaned
    data["agent_names"] = names
    save_config(data)
    return get_agent_display_names()


def get_cursor_token() -> str:
    """Cursor API key from CURSOR_API_KEY only (never from YAML)."""
    return os.environ.get("CURSOR_API_KEY", "").strip()


_CURSOR_MODELS_CACHE: dict[str, Any] = {"fetched_at": 0.0, "models": []}
_CURSOR_MODELS_CACHE_TTL_SEC = 600


def fetch_cursor_models(*, force: bool = False) -> list[dict[str, str]]:
    """
    Fetch Cursor model catalog via Cloud Agents API (cached ~10 minutes).
    Returns list of {id, name}. Raises ValueError if token missing or request fails.
    """
    now = time.time()
    if (
        not force
        and _CURSOR_MODELS_CACHE["models"]
        and (now - float(_CURSOR_MODELS_CACHE["fetched_at"])) < _CURSOR_MODELS_CACHE_TTL_SEC
    ):
        return list(_CURSOR_MODELS_CACHE["models"])

    token = get_cursor_token()
    if not token:
        raise ValueError("CURSOR_API_KEY is not set")

    basic = base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        "https://api.cursor.com/v1/models",
        headers={
            "Authorization": f"Basic {basic}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise ValueError(f"Cursor models request failed ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Cursor models request failed: {exc.reason}") from exc

    raw_list = None
    if isinstance(payload, dict):
        raw_list = payload.get("items") or payload.get("models") or payload.get("data")
    if not isinstance(raw_list, list):
        raise ValueError("Unexpected Cursor models response")

    models: list[dict[str, str]] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not model_id:
            continue
        name = item.get("displayName") or item.get("name") or model_id
        models.append({"id": str(model_id), "name": str(name)})

    models.sort(key=lambda m: m["id"].lower())
    _CURSOR_MODELS_CACHE["fetched_at"] = now
    _CURSOR_MODELS_CACHE["models"] = models
    return list(models)


def get_cursor_settings() -> dict[str, Any]:
    data = load_config()
    raw = data.get("cursor") or {}
    if not isinstance(raw, dict):
        raw = {}

    agents_raw = raw.get("agents") if isinstance(raw.get("agents"), dict) else {}
    agents: dict[str, dict[str, str]] = {}
    for agent_id, default_model in DEFAULT_CURSOR_AGENT_MODELS.items():
        entry = agents_raw.get(agent_id) if isinstance(agents_raw.get(agent_id), dict) else {}
        model = entry.get("model") if entry else None
        agents[agent_id] = {
            "model": str(model).strip() if model else default_model,
        }
    default_model = (
        DEFAULT_CURSOR["default_model"]
        if not raw.get("default_model")
        else str(raw.get("default_model")).strip()
    )
    for meta in get_custom_agents():
        agent_id = meta["id"]
        entry = agents_raw.get(agent_id) if isinstance(agents_raw.get(agent_id), dict) else {}
        model = entry.get("model") if entry else None
        if model and str(model).strip():
            agents[agent_id] = {"model": str(model).strip()}
        elif agent_id in agents_raw:
            agents[agent_id] = {"model": default_model}

    return {
        "app_name": (
            DEFAULT_CURSOR["app_name"]
            if raw.get("app_name") in (None, "")
            else str(raw.get("app_name"))
        ),
        "default_model": default_model,
        "agents": agents,
        "token_configured": bool(get_cursor_token()),
    }


def update_cursor_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    current = get_cursor_settings()

    if "app_name" in payload:
        value = payload["app_name"]
        current["app_name"] = DEFAULT_CURSOR["app_name"] if value in (None, "") else str(value)
    if "default_model" in payload:
        value = payload["default_model"]
        if value is None or str(value).strip() == "":
            raise ValueError("default_model must be a non-empty string")
        current["default_model"] = str(value).strip()

    agents_payload = payload.get("agents")
    if isinstance(agents_payload, dict):
        allowed_ids = known_agent_ids()
        for agent_id, entry in agents_payload.items():
            agent_key = str(agent_id)
            if agent_key not in allowed_ids:
                continue
            if isinstance(entry, dict):
                model = entry.get("model")
            else:
                model = entry
            if model is None or str(model).strip() == "":
                raise ValueError(f"agents.{agent_key}.model must be a non-empty string")
            current["agents"][agent_key] = {"model": str(model).strip()}

    data["cursor"] = {
        "app_name": current["app_name"],
        "default_model": current["default_model"],
        "agents": deepcopy(current["agents"]),
    }
    save_config(data)
    current["token_configured"] = bool(get_cursor_token())
    return current


def get_active_provider_settings() -> dict[str, Any]:
    provider = get_provider()
    if provider == "cursor":
        return {"provider": provider, "settings": get_cursor_settings()}
    return {"provider": provider, "settings": get_openrouter_settings()}
