"""Read/write helix.config.yaml (database + openrouter + cursor LLM)."""

from __future__ import annotations

import base64
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

from .agents import (
    AGENT_BY_ID,
    AGENT_IDS,
    AGENT_PIPELINE,
    LEGACY_AGENT_IDS,
    LEGACY_AGENT_RENAMES,
    is_builtin_agent,
)

AGENT_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
TOKEN_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_OPENROUTER_TOKEN_ENV = "OPENROUTER_TOKEN"
DEFAULT_CURSOR_TOKEN_ENV = "CURSOR_API_KEY"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_CURSOR_ADAPTER_BASE_URL = "http://127.0.0.1:8130/v1"
VALID_PROVIDERS = ("openrouter", "openai_compatible", "cursor")

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

DEFAULT_LLM_MODEL = "composer-2.5"

DEFAULT_AGENT_MODELS = {
    "guardian": DEFAULT_LLM_MODEL,
    "data-gatherer": DEFAULT_LLM_MODEL,
    "validator": DEFAULT_LLM_MODEL,
    "result-builder": DEFAULT_LLM_MODEL,
    "publisher": DEFAULT_LLM_MODEL,
}

DEFAULT_CURSOR_AGENT_MODELS = {
    "guardian": DEFAULT_LLM_MODEL,
    "data-gatherer": DEFAULT_LLM_MODEL,
    "validator": DEFAULT_LLM_MODEL,
    "result-builder": DEFAULT_LLM_MODEL,
    "publisher": DEFAULT_LLM_MODEL,
}

DEFAULT_OPENROUTER = {
    "token_env": DEFAULT_OPENROUTER_TOKEN_ENV,
    "base_url": DEFAULT_OPENROUTER_BASE_URL,
    "app_name": "Helix",
    "default_model": DEFAULT_LLM_MODEL,
    "agents": {agent_id: {"model": model} for agent_id, model in DEFAULT_AGENT_MODELS.items()},
}

DEFAULT_CURSOR = {
    "token_env": DEFAULT_CURSOR_TOKEN_ENV,
    "adapter_base_url": DEFAULT_CURSOR_ADAPTER_BASE_URL,
    "app_name": "Helix",
    "default_model": DEFAULT_LLM_MODEL,
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


DEFAULT_SQL = {
    "max_retries": 3,
    "require_row_limit": False,
    "enforce_allowlist": False,
    "forbid_select_star": True,
    "max_rows": 10000,
}


def _migrate_agent_model_map(agents: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in agents.items():
        if key in LEGACY_AGENT_IDS and key not in LEGACY_AGENT_RENAMES:
            continue
        out[LEGACY_AGENT_RENAMES.get(key, key)] = value
    return out


def _migrate_legacy_agent_ids(data: dict[str, Any]) -> dict[str, Any]:
    """Rewrite retired pipeline agent ids in agent-model maps and graphs only."""
    migrated = deepcopy(data)
    for section in ("openrouter", "cursor"):
        block = migrated.get(section)
        if isinstance(block, dict) and isinstance(block.get("agents"), dict):
            block["agents"] = _migrate_agent_model_map(block["agents"])
    deleted = migrated.get("deleted_agents")
    if isinstance(deleted, list):
        next_deleted: list[str] = []
        for item in deleted:
            value = str(item).strip()
            if value in LEGACY_AGENT_IDS and value not in LEGACY_AGENT_RENAMES:
                continue
            next_deleted.append(LEGACY_AGENT_RENAMES.get(value, value))
        migrated["deleted_agents"] = next_deleted
    graph = migrated.get("pipeline_graph")
    if isinstance(graph, dict):
        if str(graph.get("entry") or "") in LEGACY_AGENT_RENAMES:
            graph["entry"] = LEGACY_AGENT_RENAMES[str(graph["entry"])]
        for node in graph.get("nodes") or []:
            if isinstance(node, dict):
                node_id = str(node.get("id") or "")
                if node_id in LEGACY_AGENT_RENAMES:
                    node["id"] = LEGACY_AGENT_RENAMES[node_id]
        for edge in graph.get("edges") or []:
            if not isinstance(edge, dict):
                continue
            for end in ("source", "target"):
                value = str(edge.get(end) or "")
                if value in LEGACY_AGENT_RENAMES:
                    edge[end] = LEGACY_AGENT_RENAMES[value]
    return migrated


def _drop_stale_pipeline_graph(data: dict[str, Any]) -> dict[str, Any]:
    graph = data.get("pipeline_graph")
    if not isinstance(graph, dict):
        return data
    node_ids = {
        str(node.get("id") or "").strip()
        for node in (graph.get("nodes") or [])
        if isinstance(node, dict)
    }
    if node_ids & LEGACY_AGENT_IDS:
        data = dict(data)
        data.pop("pipeline_graph", None)
        data.pop("pipeline_flow", None)
    return data


def load_config() -> dict[str, Any]:
    path = ensure_config_exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    migrated = _drop_stale_pipeline_graph(_migrate_legacy_agent_ids(data))
    if not isinstance(migrated, dict):
        migrated = {}
    if migrated != data:
        save_config(migrated)
        return migrated
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


def _explicit_warehouse_engine(db: dict[str, Any]) -> str | None:
    from .db_dialects.base import ENGINE_ALIASES

    raw = str(db.get("engine") or "").strip().lower()
    if not raw:
        return None
    engine = ENGINE_ALIASES.get(raw)
    if engine in ("sqlserver", "postgresql"):
        return engine
    return None


def _finalize_database(db: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize settings. Sample SQLite is only used when the engine is sqlite."""
    from .db_dialects.base import normalize_engine
    from .sample_database import SAMPLE_FILENAME, is_sample_db_path, resolve_sqlite_path

    raw = db if isinstance(db, dict) else {}
    warehouse_engine = _explicit_warehouse_engine(raw)
    merged = {**DEFAULT_DATABASE, **raw}
    if warehouse_engine:
        merged["engine"] = warehouse_engine
        leftover_name = str(merged.get("name") or merged.get("path") or "").strip()
        if is_sample_db_path(leftover_name):
            merged["name"] = ""
            merged["path"] = ""
    elif not is_user_provided_database(merged):
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
    else:
        merged["path"] = ""
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
    conn = payload.get("connection_string")
    engine_hint = _explicit_warehouse_engine(payload)
    use_connection_string = conn is not None and str(conn).strip() != ""
    if use_connection_string and engine_hint in ("sqlserver", "postgresql"):
        if str(conn).strip().lower().startswith("file:"):
            use_connection_string = False
    if use_connection_string:
        current = connection_string_to_database(str(conn))
        if engine_hint:
            current["engine"] = engine_hint
    else:
        current = get_database_settings()
        if engine_hint:
            current["engine"] = engine_hint
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
    if current.get("engine") == "sqlite" and not is_user_provided_database(current):
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
        "Connection Timeout=15",
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
    """LLM API key from Settings (config), then optional env fallback."""
    data = load_config()
    token = _section_stored_token(data.get("openrouter"))
    if token:
        return token
    return os.environ.get(get_openrouter_token_env(), "").strip()


def _normalize_base_url(raw: Any) -> str:
    return str(raw or "").strip().rstrip("/")


def _rewrite_unresolvable_hostname_to_localhost(base_url: str) -> str:
    """
    Rewrite an unresolvable LLM hostname to localhost.

    Why: config may point at a container hostname (e.g. `cursor-openai-adapter-api`)
    which is only resolvable from inside Docker. When running on the host, DNS
    will fail, and the pipeline should fall back to `127.0.0.1`.
    """
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if not hostname:
        return base_url

    try:
        socket.getaddrinfo(hostname, None)
        return base_url
    except OSError:
        netloc = "127.0.0.1"
        if parsed.port:
            netloc = f"127.0.0.1:{parsed.port}"
        return parsed._replace(netloc=netloc).geturl()


def get_cursor_adapter_base_url() -> str:
    """OpenAI-compatible chat bridge for Cursor Cloud (local cursor-api by default)."""
    data = load_config()
    raw = data.get("cursor") or {}
    if not isinstance(raw, dict):
        raw = {}
    stored = _rewrite_unresolvable_hostname_to_localhost(
        _normalize_base_url(raw.get("adapter_base_url"))
    )
    if stored:
        return stored
    return DEFAULT_CURSOR_ADAPTER_BASE_URL


def get_llm_base_url() -> str:
    """Chat/models host: Cursor adapter, OpenRouter stored URL, or OpenRouter default."""
    if get_provider() == "cursor":
        return get_cursor_adapter_base_url()
    data = load_config()
    raw = data.get("openrouter") or {}
    if not isinstance(raw, dict):
        raw = {}
    stored = _rewrite_unresolvable_hostname_to_localhost(
        _normalize_base_url(raw.get("base_url"))
    )
    if stored:
        return stored
    if get_provider() == "openrouter":
        return DEFAULT_OPENROUTER_BASE_URL
    return ""


DEFAULT_LLM_TIMEOUT_SECONDS = 600


def get_llm_timeout_seconds() -> int:
    """HTTP read timeout for chat/completions (pipeline agents can run long)."""
    data = load_config()
    raw = data.get("openrouter") or {}
    if not isinstance(raw, dict):
        raw = {}
    try:
        value = int(raw.get("timeout_seconds") or DEFAULT_LLM_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        value = DEFAULT_LLM_TIMEOUT_SECONDS
    return max(30, min(value, 900))


def get_cursor_token() -> str:
    """Cursor API key from Settings (config), then optional env fallback."""
    data = load_config()
    token = _section_stored_token(data.get("cursor"))
    if token:
        return token
    return os.environ.get(get_cursor_token_env(), "").strip()


_MODELS_CACHE: dict[str, Any] = {"fetched_at": 0.0, "models": [], "base_url": ""}
_MODELS_CACHE_TTL_SEC = 600


def _catalog_with_auto(models: list[dict[str, str]]) -> list[dict[str, str]]:
    out = list(models)
    if not any(str(item.get("id", "")).lower() == "auto" for item in out):
        out.append({"id": "auto", "name": "Auto"})
    out.sort(key=lambda item: str(item.get("name") or item.get("id") or "").lower())
    return out


def fetch_openrouter_models(*, force: bool = False) -> list[dict[str, str]]:
    """
    Fetch the LLM model catalog from {base_url}/models (cached ~10 minutes).
    Returns list of {id, name}. Raises ValueError if token/base URL missing or request fails.
    """
    now = time.time()
    base_url = get_llm_base_url()
    if (
        not force
        and _MODELS_CACHE["models"]
        and _MODELS_CACHE.get("base_url") == base_url
        and (now - float(_MODELS_CACHE["fetched_at"])) < _MODELS_CACHE_TTL_SEC
    ):
        return list(_MODELS_CACHE["models"])

    token = get_openrouter_token()
    if not token:
        raise ValueError("API key is not set")
    if not base_url:
        raise ValueError("Base URL is not set")

    req = urllib.request.Request(
        f"{base_url}/models",
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
        raise ValueError(f"Models request failed ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Models request failed: {exc.reason}") from exc

    raw_list = None
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            raw_list = payload.get("data")
        elif isinstance(payload.get("models"), list):
            raw_list = payload.get("models")
    elif isinstance(payload, list):
        raw_list = payload
    if not isinstance(raw_list, list):
        raise ValueError("Unexpected models response")

    models: list[dict[str, str]] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not model_id:
            continue
        name = item.get("name") or model_id
        models.append({"id": str(model_id), "name": str(name)})

    models = _catalog_with_auto(models)
    _MODELS_CACHE["fetched_at"] = now
    _MODELS_CACHE["models"] = models
    _MODELS_CACHE["base_url"] = base_url
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
    stored_base_url = _normalize_base_url(raw.get("base_url"))
    if stored_base_url:
        base_url = stored_base_url
    elif get_provider() == "openrouter":
        base_url = DEFAULT_OPENROUTER_BASE_URL
    else:
        base_url = ""
    return {
        "base_url": base_url,
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
    stored_base_url = _normalize_base_url(raw.get("base_url"))
    if "base_url" in payload:
        stored_base_url = _normalize_base_url(payload.get("base_url"))
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
        "base_url": stored_base_url,
        "app_name": current["app_name"],
        "default_model": current["default_model"],
        "agents": deepcopy(current["agents"]),
    }
    if stored_token:
        section["token"] = stored_token
    data["openrouter"] = section
    save_config(data)
    _MODELS_CACHE["fetched_at"] = 0.0
    _MODELS_CACHE["models"] = []
    _MODELS_CACHE["base_url"] = ""
    return get_openrouter_settings()


def get_provider() -> str:
    data = load_config()
    raw = data.get("provider")
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in VALID_PROVIDERS:
            return value
    return DEFAULT_PROVIDER


def update_provider(provider: str) -> str:
    value = (provider or "").strip().lower()
    if value not in VALID_PROVIDERS:
        raise ValueError(
            "provider must be openrouter, openai_compatible, or cursor"
        )
    data = load_config()
    data["provider"] = value
    save_config(data)
    return value


# Max data-URL length for company logo (~300KB binary as base64).
_MAX_BRANDING_LOGO_CHARS = 400_000


def get_branding() -> dict[str, str]:
    data = load_config()
    raw = data.get("branding") if isinstance(data.get("branding"), dict) else {}
    name = raw.get("company_name")
    logo = raw.get("company_logo_data_url")
    return {
        "company_name": "" if name in (None, "") else str(name).strip(),
        "company_logo_data_url": (
            ""
            if logo in (None, "")
            else str(logo).strip()[:_MAX_BRANDING_LOGO_CHARS]
        ),
    }


def update_branding(payload: dict[str, Any]) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("branding payload must be an object")
    current = get_branding()
    if "company_name" in payload:
        value = payload.get("company_name")
        current["company_name"] = (
            "" if value in (None, "") else str(value).strip()
        )
    if "company_logo_data_url" in payload:
        value = payload.get("company_logo_data_url")
        if value in (None, ""):
            current["company_logo_data_url"] = ""
        else:
            text = str(value).strip()
            if text and not text.startswith("data:image/"):
                raise ValueError(
                    "company_logo_data_url must be an image data URL or empty"
                )
            if len(text) > _MAX_BRANDING_LOGO_CHARS:
                raise ValueError("company_logo_data_url is too large")
            current["company_logo_data_url"] = text
    data = load_config()
    data["branding"] = {
        "company_name": current["company_name"],
        "company_logo_data_url": current["company_logo_data_url"],
    }
    save_config(data)
    return get_branding()


def detect_cursor_install() -> dict[str, Any]:
    """Return whether the Cursor desktop app appears installed on this machine."""
    import shutil

    which = shutil.which("cursor")
    if which and Path(which).is_file():
        return {
            "installed": True,
            "detail": "",
            "path": which,
        }

    candidates: list[Path] = []
    local_app = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app:
        candidates.append(Path(local_app) / "Programs" / "cursor" / "Cursor.exe")
        candidates.append(Path(local_app) / "Programs" / "Cursor" / "Cursor.exe")
    program_files = os.environ.get("ProgramFiles", "").strip()
    if program_files:
        candidates.append(Path(program_files) / "Cursor" / "Cursor.exe")
    home = Path.home()
    candidates.extend(
        [
            home / "AppData" / "Local" / "Programs" / "cursor" / "Cursor.exe",
            home / "Applications" / "Cursor.app",
            Path("/Applications/Cursor.app"),
            Path("/usr/bin/cursor"),
            Path("/usr/local/bin/cursor"),
        ]
    )
    for path in candidates:
        try:
            if path.exists():
                return {
                    "installed": True,
                    "detail": "",
                    "path": str(path),
                }
        except OSError:
            continue

    return {
        "installed": False,
        "detail": (
            "Cursor is not installed on this machine. "
            "Install it from https://cursor.com then try again."
        ),
        "path": "",
    }


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
        if not agent_id or agent_id in seen:
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
                "builtin": agent_id in AGENT_BY_ID,
                "disabled": bool(entry.get("disabled")),
            }
        )
    return agents


def _apply_agent_profile(meta: dict[str, Any], profiles: dict[str, Any]) -> dict[str, Any]:
    item = dict(meta)
    profile = profiles.get(meta["id"])
    if not isinstance(profile, dict):
        return item
    if profile.get("name"):
        item["name"] = str(profile["name"]).strip()
    if "description" in profile:
        item["description"] = str(profile.get("description") or "").strip()
    return item


def restore_seed_pipeline_agents() -> None:
    """Bring back seed pipeline agents hidden by deleted_agents (one-time)."""
    data = load_config()
    if data.get("pipeline_agents_restored"):
        return
    deleted = get_deleted_agent_ids()
    data["deleted_agents"] = sorted(deleted - set(AGENT_IDS))
    data["pipeline_agents_restored"] = True
    save_config(data)


def get_all_agent_metas() -> list[dict[str, Any]]:
    restore_seed_pipeline_agents()
    disabled = get_disabled_agent_ids()
    deleted = get_deleted_agent_ids()
    data = load_config()
    profiles = data.get("agent_profiles") if isinstance(data.get("agent_profiles"), dict) else {}
    custom_by_id = {item["id"]: item for item in get_custom_agents()}
    result: list[dict[str, Any]] = []
    for meta in AGENT_PIPELINE:
        if meta["id"] in deleted:
            continue
        base = {**meta, "builtin": True, "disabled": meta["id"] in disabled}
        custom = custom_by_id.get(meta["id"])
        if custom:
            for key in ("name", "description", "disabled"):
                if custom.get(key) not in (None, ""):
                    base[key] = custom[key]
            base["disabled"] = bool(custom.get("disabled")) if "disabled" in custom else base["disabled"]
        result.append(_apply_agent_profile(base, profiles))
    for custom in custom_by_id.values():
        if custom["id"] in AGENT_BY_ID or custom["id"] in deleted:
            continue
        result.append(_apply_agent_profile(custom, profiles))
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
    from .agents import resolve_agent_definition_id

    definition_id = resolve_agent_definition_id(agent_id)
    for meta in get_all_agent_metas():
        if meta["id"] == definition_id:
            return dict(meta)
    raise KeyError(f"Unknown agent: {agent_id}")


def create_custom_agent(
    agent_id: str,
    name: str,
    description: str = "",
) -> dict[str, Any]:
    cleaned_id = (agent_id or "").strip()
    if not AGENT_ID_RE.match(cleaned_id):
        raise ValueError(
            "id must be lowercase letters, digits, underscores, or hyphens, starting with a letter"
        )
    data = load_config()
    deleted = get_deleted_agent_ids()
    if cleaned_id in deleted:
        deleted.discard(cleaned_id)
        data["deleted_agents"] = sorted(deleted)
        save_config(data)
        if is_builtin_agent(cleaned_id):
            return update_agent_fields(
                cleaned_id,
                name=name,
                description=description,
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
    skills_path = store.skills_dir() / cleaned_id
    skills_path.mkdir(parents=True, exist_ok=True)

    return {
        "id": cleaned_id,
        "name": cleaned_name,
        "description": cleaned_description,
        "builtin": False,
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

    profiles = data.get("agent_profiles") if isinstance(data.get("agent_profiles"), dict) else {}
    if cleaned_id in profiles:
        profiles = dict(profiles)
        profiles.pop(cleaned_id, None)
        data["agent_profiles"] = profiles

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
        data["pipeline_flow"] = None

    save_config(data)

    from . import markdown_store as store

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


def update_agent_fields(
    agent_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    if agent_id not in known_agent_ids():
        raise KeyError(f"Unknown agent: {agent_id}")
    data = load_config()
    profiles = data.get("agent_profiles") if isinstance(data.get("agent_profiles"), dict) else {}
    profile = dict(profiles.get(agent_id) or {}) if isinstance(profiles.get(agent_id), dict) else {}

    if name is not None:
        update_agent_display_name(agent_id, name)
        data = load_config()
        profiles = data.get("agent_profiles") if isinstance(data.get("agent_profiles"), dict) else {}
        profile = dict(profiles.get(agent_id) or {}) if isinstance(profiles.get(agent_id), dict) else {}

    if description is not None:
        cleaned_description = str(description).strip()
        if len(cleaned_description) > 500:
            raise ValueError("description must be at most 500 characters")
        profile["description"] = cleaned_description

    if not is_builtin_agent(agent_id):
        custom = data.get("custom_agents")
        if isinstance(custom, list):
            for entry in custom:
                if isinstance(entry, dict) and str(entry.get("id") or "").strip() == agent_id:
                    if "description" in profile:
                        entry["description"] = profile["description"]
                    break
        data["custom_agents"] = custom

    if profile:
        profiles[agent_id] = profile
        data["agent_profiles"] = profiles
    save_config(data)
    return get_agent_meta(agent_id)


def agent_company_label(agent_id: str) -> str:
    from .agents import resolve_agent_definition_id

    definition_id = resolve_agent_definition_id(agent_id)
    try:
        meta = get_agent_meta(definition_id)
    except KeyError:
        return agent_id
    names = get_agent_display_names()
    role = names.get(definition_id, meta.get("name") or definition_id)
    return str(role or agent_id).strip()


_CURSOR_MODELS_CACHE: dict[str, Any] = {"fetched_at": 0.0, "models": []}
_CURSOR_MODELS_CACHE_TTL_SEC = 600
CURSOR_CLOUD_API_BASE = "https://api.cursor.com"


def cursor_cloud_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    """Call Cursor Cloud Agents API with Basic auth (API key as username)."""
    token = get_cursor_token()
    if not token:
        raise ValueError("Cursor API key is not set")
    basic = base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")
    url = f"{CURSOR_CLOUD_API_BASE}{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Basic {basic}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ValueError(f"Cursor API request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Cursor API request failed: {exc.reason}") from exc
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Cursor API returned non-JSON") from exc


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

    payload = cursor_cloud_json("GET", "/v1/models")

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

    models = _catalog_with_auto(models)
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
    adapter = _rewrite_unresolvable_hostname_to_localhost(
        _normalize_base_url(raw.get("adapter_base_url"))
    ) or DEFAULT_CURSOR_ADAPTER_BASE_URL
    return {
        "app_name": (
            DEFAULT_CURSOR["app_name"]
            if raw.get("app_name") in (None, "")
            else str(raw.get("app_name"))
        ),
        "default_model": default_model,
        "agents": agents,
        "adapter_base_url": adapter,
        "token_configured": bool(token),
    }


def update_cursor_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    current = get_cursor_settings()
    raw = data.get("cursor") if isinstance(data.get("cursor"), dict) else {}
    stored_token = _section_stored_token(raw)
    stored_env = _token_env_from_section(raw, DEFAULT_CURSOR_TOKEN_ENV)
    stored_adapter = (
        _rewrite_unresolvable_hostname_to_localhost(
            _normalize_base_url(raw.get("adapter_base_url"))
        )
        or DEFAULT_CURSOR_ADAPTER_BASE_URL
    )

    if "token" in payload:
        incoming = payload.get("token")
        if incoming is not None and str(incoming).strip():
            stored_token = str(incoming).strip()
    if "token_env" in payload:
        stored_env = _normalize_token_env(
            payload["token_env"], DEFAULT_CURSOR_TOKEN_ENV
        )
    if "adapter_base_url" in payload:
        value = payload.get("adapter_base_url")
        if value is None or str(value).strip() == "":
            stored_adapter = DEFAULT_CURSOR_ADAPTER_BASE_URL
        else:
            stored_adapter = (
                _rewrite_unresolvable_hostname_to_localhost(
                    _normalize_base_url(value)
                )
                or DEFAULT_CURSOR_ADAPTER_BASE_URL
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
        "adapter_base_url": stored_adapter,
        "app_name": current["app_name"],
        "default_model": current["default_model"],
        "agents": deepcopy(current["agents"]),
    }
    if stored_token:
        section["token"] = stored_token
    data["cursor"] = section
    save_config(data)
    return get_cursor_settings()


def get_sql_settings() -> dict[str, Any]:
    data = load_config()
    raw = data.get("sql")
    if not isinstance(raw, dict):
        raw = data.get("sql_guardian") if isinstance(data.get("sql_guardian"), dict) else {}
    merged = {**DEFAULT_SQL, **raw}
    try:
        merged["max_retries"] = max(1, int(merged.get("max_retries") or 3))
    except (TypeError, ValueError):
        merged["max_retries"] = 3
    try:
        merged["max_rows"] = max(1, int(merged.get("max_rows") or 10000))
    except (TypeError, ValueError):
        merged["max_rows"] = 10000
    merged["require_row_limit"] = bool(merged.get("require_row_limit", False))
    merged["enforce_allowlist"] = bool(merged.get("enforce_allowlist", False))
    merged["forbid_select_star"] = bool(merged.get("forbid_select_star", True))
    return merged


def get_active_provider_settings() -> dict[str, Any]:
    provider = get_provider()
    if provider == "cursor":
        return {"provider": provider, "settings": get_cursor_settings()}
    return {"provider": provider, "settings": get_openrouter_settings()}


def get_agent_model(agent_id: str) -> str:
    settings = get_active_provider_settings()["settings"]
    agents = settings.get("agents") if isinstance(settings.get("agents"), dict) else {}
    entry = agents.get(agent_id)
    if isinstance(entry, dict):
        model = str(entry.get("model") or "").strip()
        if model and model != "auto":
            return model
    default = str(settings.get("default_model") or "").strip()
    if default and default != "auto":
        return default
    return DEFAULT_LLM_MODEL
