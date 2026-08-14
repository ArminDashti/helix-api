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
TOKEN_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_OPENROUTER_TOKEN_ENV = "OPENROUTER_TOKEN"
DEFAULT_CURSOR_TOKEN_ENV = "CURSOR_API_KEY"

DEFAULT_DATABASE = {
    # Built-in AdventureWorks LT sample SQLite (seeded on first start).
    "engine": "sqlite",
    "host": "",
    "port": 0,
    "name": "helix-sample.sqlite",
    "user": "",
    "password": "",
    "sslmode": "prefer",
    "driver": "ODBC Driver 18 for SQL Server",
    "trust_server_certificate": True,
    "encrypt": True,
    "path": "",
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
    "token_env": DEFAULT_OPENROUTER_TOKEN_ENV,
    "app_name": "Helix",
    "default_model": "openai/gpt-4o-mini",
    "agents": {agent_id: {"model": model} for agent_id, model in DEFAULT_AGENT_MODELS.items()},
}

DEFAULT_CURSOR = {
    "token_env": DEFAULT_CURSOR_TOKEN_ENV,
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


def is_user_provided_database(db: dict[str, Any] | None) -> bool:
    """True when the user configured a real warehouse (not the built-in sample)."""
    from .db_dialects.base import normalize_engine
    from .sample_database import is_sample_db_path

    if not isinstance(db, dict) or not db:
        return False
    engine = normalize_engine(db.get("engine"))
    name = str(db.get("name") or db.get("path") or "").strip()
    host = str(db.get("host") or "").strip()
    if engine == "sqlite":
        return bool(name) and not is_sample_db_path(name)
    return bool(host and name)


def _finalize_database(db: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize settings; missing warehouse config becomes sqlite + sample file."""
    from .db_dialects.base import normalize_engine
    from .sample_database import SAMPLE_FILENAME, resolve_sqlite_path

    raw = db if isinstance(db, dict) else {}
    merged = {**DEFAULT_DATABASE, **raw}
    if not is_user_provided_database(merged):
        merged = deepcopy(DEFAULT_DATABASE)
    merged["engine"] = normalize_engine(merged.get("engine"))
    if merged["engine"] == "sqlite":
        default_port = 0
    elif merged["engine"] == "postgresql":
        default_port = 5432
    else:
        default_port = 1433
    try:
        merged["port"] = int(merged.get("port") or default_port)
    except (TypeError, ValueError):
        merged["port"] = default_port
    merged["trust_server_certificate"] = bool(merged.get("trust_server_certificate", True))
    merged["encrypt"] = bool(merged.get("encrypt", True))
    for key in (
        "host",
        "name",
        "user",
        "password",
        "driver",
        "sslmode",
        "path",
    ):
        merged[key] = "" if merged.get(key) is None else str(merged[key])
    if merged["engine"] == "sqlite":
        raw_name = (merged.get("name") or merged.get("path") or SAMPLE_FILENAME).strip()
        resolved = resolve_sqlite_path(raw_name or SAMPLE_FILENAME)
        merged["name"] = str(resolved)
        merged["path"] = str(resolved)
    return merged


def get_database_engine() -> str:
    from .db_dialects.base import normalize_engine

    db = get_database_settings()
    return normalize_engine(db.get("engine"))


def get_database_settings() -> dict[str, Any]:
    data = load_config()
    db = data.get("database") or {}
    if not isinstance(db, dict):
        db = {}
    return _finalize_database(db)


def update_database_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    if "connection_string" in payload and payload.get("connection_string") is not None:
        current = connection_string_to_database(str(payload["connection_string"]))
    else:
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
        elif key == "engine":
            from .db_dialects.base import normalize_engine

            current[key] = normalize_engine(str(value))
        else:
            current[key] = "" if value is None else str(value)
    current = _finalize_database(current)
    data["database"] = current
    save_config(data)
    if not is_user_provided_database(current):
        from .sample_database import ensure_sample_database

        try:
            ensure_sample_database()
        except PermissionError:
            pass
    return current


def database_to_connection_string(db: dict[str, Any] | None = None) -> str:
    from .db_dialects.base import normalize_engine

    db = db or get_database_settings()
    engine = normalize_engine(db.get("engine"))
    if engine == "postgresql":
        parts = [
            f"host={db['host']}",
            f"port={db['port']}",
            f"dbname={db['name']}",
            f"user={db['user']}",
            f"password={db['password']}",
        ]
        sslmode = (db.get("sslmode") or "prefer").strip()
        if sslmode:
            parts.append(f"sslmode={sslmode}")
        return " ".join(parts)
    if engine == "sqlite":
        from .sample_database import resolve_sqlite_path

        path = resolve_sqlite_path(db.get("name") or db.get("path") or "")
        return f"file:{path}"
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


def connection_string_to_database(conn: str) -> dict[str, Any]:
    """Parse a connection string into database settings."""
    if not isinstance(conn, str) or not conn.strip():
        raise ValueError("connection_string must be a non-empty string")

    current = get_database_settings()
    stripped = conn.strip()
    if stripped.lower().startswith("file:"):
        current["engine"] = "sqlite"
        current["name"] = stripped[5:]
        current["path"] = current["name"]
        return current

    if "host=" in stripped and "dbname=" in stripped:
        parts: dict[str, str] = {}
        for chunk in stripped.split():
            if "=" not in chunk:
                continue
            key, value = chunk.split("=", 1)
            parts[key.strip().lower()] = value.strip()
        current["engine"] = "postgresql"
        current["host"] = parts.get("host", current["host"])
        if "port" in parts:
            try:
                current["port"] = int(parts["port"])
            except ValueError as exc:
                raise ValueError("connection_string port must be an integer") from exc
        current["name"] = parts.get("dbname", current["name"])
        current["user"] = parts.get("user", current["user"])
        current["password"] = parts.get("password", current["password"])
        if "sslmode" in parts:
            current["sslmode"] = parts["sslmode"]
        return current

    parts = {}
    for chunk in stripped.split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        parts[key.strip().lower()] = value.strip()

    current["engine"] = "sqlserver"
    driver = parts.get("driver")
    if driver:
        current["driver"] = driver.strip("{}")

    server = parts.get("server") or parts.get("data source") or parts.get("address")
    if server:
        if "," in server:
            host, port_s = server.rsplit(",", 1)
            current["host"] = host.strip()
            try:
                current["port"] = int(port_s.strip())
            except ValueError as exc:
                raise ValueError("connection_string Server port must be an integer") from exc
        else:
            current["host"] = server.strip()

    if "database" in parts or "initial catalog" in parts:
        current["name"] = parts.get("database") or parts.get("initial catalog") or ""
    if "uid" in parts or "user id" in parts or "username" in parts:
        current["user"] = (
            parts.get("uid") or parts.get("user id") or parts.get("username") or ""
        )
    if "pwd" in parts or "password" in parts:
        current["password"] = parts.get("pwd") or parts.get("password") or ""

    encrypt = parts.get("encrypt")
    if encrypt is not None:
        current["encrypt"] = encrypt.lower() in ("yes", "true", "1")
    trust = parts.get("trustservercertificate")
    if trust is not None:
        current["trust_server_certificate"] = trust.lower() in ("yes", "true", "1")

    return current


def _normalize_token_env(value: Any, default: str) -> str:
    name = default if value is None else str(value).strip()
    if not name:
        name = default
    if not TOKEN_ENV_RE.match(name):
        raise ValueError("token_env must be a valid environment variable name")
    return name


def _token_env_from_section(raw: dict[str, Any], default: str) -> str:
    try:
        return _normalize_token_env(raw.get("token_env"), default)
    except ValueError:
        return default


def get_openrouter_token_env() -> str:
    data = load_config()
    raw = data.get("openrouter") or {}
    if not isinstance(raw, dict):
        raw = {}
    return _token_env_from_section(raw, DEFAULT_OPENROUTER_TOKEN_ENV)


def get_cursor_token_env() -> str:
    data = load_config()
    raw = data.get("cursor") or {}
    if not isinstance(raw, dict):
        raw = {}
    return _token_env_from_section(raw, DEFAULT_CURSOR_TOKEN_ENV)


def _section_stored_token(raw: Any) -> str:
    if not isinstance(raw, dict):
        return ""
    return str(raw.get("token") or "").strip()


def get_openrouter_token() -> str:
    """OpenRouter token from Settings (config), then optional env fallback."""
    data = load_config()
    token = _section_stored_token(data.get("openrouter"))
    if token:
        return token
    return os.environ.get(get_openrouter_token_env(), "").strip()


def get_cursor_token() -> str:
    """Cursor API key from Settings (config), then optional env fallback."""
    data = load_config()
    token = _section_stored_token(data.get("cursor"))
    if token:
        return token
    return os.environ.get(get_cursor_token_env(), "").strip()


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
        raise ValueError("OpenRouter API key is not set")

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
    known = known_agent_ids()
    agents: dict[str, dict[str, str]] = {}
    for agent_id, default_model in DEFAULT_AGENT_MODELS.items():
        if agent_id not in known:
            continue
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

    token = get_openrouter_token()
    return {
        "app_name": (
            DEFAULT_OPENROUTER["app_name"]
            if raw.get("app_name") in (None, "")
            else str(raw.get("app_name"))
        ),
        "default_model": default_model,
        "agents": agents,
        "token_configured": bool(token),
    }


def update_openrouter_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    current = get_openrouter_settings()
    raw = data.get("openrouter") if isinstance(data.get("openrouter"), dict) else {}
    stored_token = _section_stored_token(raw)
    stored_env = _token_env_from_section(raw, DEFAULT_OPENROUTER_TOKEN_ENV)

    if "token" in payload:
        incoming = payload.get("token")
        if incoming is not None and str(incoming).strip():
            stored_token = str(incoming).strip()
    if "token_env" in payload:
        stored_env = _normalize_token_env(
            payload["token_env"], DEFAULT_OPENROUTER_TOKEN_ENV
        )
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

    section: dict[str, Any] = {
        "token_env": stored_env,
        "app_name": current["app_name"],
        "default_model": current["default_model"],
        "agents": deepcopy(current["agents"]),
    }
    if stored_token:
        section["token"] = stored_token
    data["openrouter"] = section
    save_config(data)
    return get_openrouter_settings()


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
                "disabled": bool(entry.get("disabled")),
            }
        )
    return agents


def get_all_agent_metas() -> list[dict[str, Any]]:
    disabled = get_disabled_agent_ids()
    deleted = get_deleted_agent_ids()
    result: list[dict[str, Any]] = []
    for meta in AGENT_PIPELINE:
        if meta["id"] in deleted:
            continue
        result.append({**meta, "builtin": True, "disabled": meta["id"] in disabled})
    result.extend(get_custom_agents())
    return result


def get_deleted_agent_ids() -> set[str]:
    data = load_config()
    raw = data.get("deleted_agents")
    if not isinstance(raw, list):
        return set()
    return {str(item).strip() for item in raw if str(item).strip()}


def get_disabled_agent_ids() -> set[str]:
    data = load_config()
    raw = data.get("disabled_agents")
    if not isinstance(raw, list):
        return set()
    return {str(item).strip() for item in raw if str(item).strip()}


def set_agent_disabled(agent_id: str, disabled: bool) -> dict[str, Any]:
    if agent_id not in known_agent_ids():
        raise KeyError(f"Unknown agent: {agent_id}")
    data = load_config()
    if is_builtin_agent(agent_id):
        current = get_disabled_agent_ids()
        if disabled:
            current.add(agent_id)
        else:
            current.discard(agent_id)
        data["disabled_agents"] = sorted(current)
    else:
        custom = data.get("custom_agents")
        if not isinstance(custom, list):
            raise KeyError(f"Unknown agent: {agent_id}")
        found = False
        for entry in custom:
            if isinstance(entry, dict) and str(entry.get("id") or "").strip() == agent_id:
                entry["disabled"] = bool(disabled)
                found = True
                break
        if not found:
            raise KeyError(f"Unknown agent: {agent_id}")
        data["custom_agents"] = custom
    save_config(data)
    return get_agent_meta(agent_id)


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
    if cleaned_id not in known_agent_ids():
        raise KeyError(f"Unknown agent: {cleaned_id}")
    data = load_config()

    if is_builtin_agent(cleaned_id):
        deleted = get_deleted_agent_ids()
        deleted.add(cleaned_id)
        data["deleted_agents"] = sorted(deleted)
        disabled = get_disabled_agent_ids()
        disabled.discard(cleaned_id)
        data["disabled_agents"] = sorted(disabled)
    else:
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

    graph = data.get("pipeline_graph")
    if isinstance(graph, dict):
        nodes = [
            node
            for node in (graph.get("nodes") or [])
            if isinstance(node, dict) and str(node.get("id") or "").strip() != cleaned_id
        ]
        edges = [
            edge
            for edge in (graph.get("edges") or [])
            if isinstance(edge, dict)
            and str(edge.get("source") or "").strip() != cleaned_id
            and str(edge.get("target") or "").strip() != cleaned_id
        ]
        entry = str(graph.get("entry") or "").strip()
        if entry == cleaned_id:
            entry = str(nodes[0].get("id") or "").strip() if nodes else ""
        data["pipeline_graph"] = {"entry": entry or None, "nodes": nodes, "edges": edges}

    save_config(data)

    from . import markdown_store as store

    instr_path = store.instructions_dir() / f"{cleaned_id}.md"
    if instr_path.exists():
        instr_path.unlink()
    store.save_assignments(store.load_assignments())
    store.save_skill_assignments(store.load_skill_assignments())


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
        raise ValueError("Cursor API key is not set")

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
    known = known_agent_ids()
    agents: dict[str, dict[str, str]] = {}
    for agent_id, default_model in DEFAULT_CURSOR_AGENT_MODELS.items():
        if agent_id not in known:
            continue
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

    token = get_cursor_token()
    return {
        "app_name": (
            DEFAULT_CURSOR["app_name"]
            if raw.get("app_name") in (None, "")
            else str(raw.get("app_name"))
        ),
        "default_model": default_model,
        "agents": agents,
        "token_configured": bool(token),
    }


def update_cursor_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    current = get_cursor_settings()
    raw = data.get("cursor") if isinstance(data.get("cursor"), dict) else {}
    stored_token = _section_stored_token(raw)
    stored_env = _token_env_from_section(raw, DEFAULT_CURSOR_TOKEN_ENV)

    if "token" in payload:
        incoming = payload.get("token")
        if incoming is not None and str(incoming).strip():
            stored_token = str(incoming).strip()
    if "token_env" in payload:
        stored_env = _normalize_token_env(
            payload["token_env"], DEFAULT_CURSOR_TOKEN_ENV
        )
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

    section: dict[str, Any] = {
        "token_env": stored_env,
        "app_name": current["app_name"],
        "default_model": current["default_model"],
        "agents": deepcopy(current["agents"]),
    }
    if stored_token:
        section["token"] = stored_token
    data["cursor"] = section
    save_config(data)
    return get_cursor_settings()


def get_active_provider_settings() -> dict[str, Any]:
    provider = get_provider()
    if provider == "cursor":
        return {"provider": provider, "settings": get_cursor_settings()}
    return {"provider": provider, "settings": get_openrouter_settings()}
