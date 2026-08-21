"""HTTP views for Helix API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import markdown_store as store
from . import db_sql
from . import docs_catalog
from . import logs_store
from . import results_store
from .config_loader import (
    create_custom_agent,
    database_to_connection_string,
    delete_custom_agent,
    detect_cursor_install,
    fetch_cursor_models,
    fetch_openrouter_models,
    get_active_provider_settings,
    get_agent_display_names,
    get_agent_meta,
    get_cursor_settings,
    get_cursor_token,
    get_database_engine,
    get_database_settings,
    get_llm_base_url,
    get_openrouter_settings,
    get_openrouter_token,
    get_provider,
    known_agent_ids,
    set_agent_disabled,
    update_agent_display_name,
    update_agent_fields,
    update_cursor_settings,
    update_database_settings,
    update_openrouter_settings,
    update_provider,
)
from .demo import (
    VALID_CHART_TYPES,
    VALID_LANGUAGES,
    VALID_MODES,
    VALID_REPORT_TYPES,
)
from .pipeline_graph import (
    get_pipeline_bundle,
    reset_pipeline_bundle,
    update_pipeline_bundle,
)
from .llm_client import require_llm
from . import org
from .pipeline_run import pipeline_events, run_pipeline_sync


def _json_body(request: HttpRequest) -> dict[str, Any]:
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON body") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def _record_log_error(
    *,
    kind: str,
    message: str,
    prompt: str = "",
    mode: str = "",
    language: str = "",
    path: str = "",
    status_code: int | None = None,
    sql: str = "",
) -> None:
    logs_store.append_error(
        kind=kind,
        message=message,
        prompt=prompt,
        mode=mode,
        language=language,
        sql=sql,
        path=path,
        status_code=status_code,
    )


# --- Health / connectivity ---


@csrf_exempt
@require_http_methods(["GET"])
def health(request: HttpRequest) -> JsonResponse:
    """Report connectivity for helix-api, SQL database, and LLM providers."""
    checked_at = datetime.now(timezone.utc).isoformat()

    def stamp(block: dict[str, Any]) -> dict[str, Any]:
        out = dict(block)
        if "detail" not in out:
            out["detail"] = ""
        out["checked_at"] = checked_at
        return out

    api = stamp({"status": "connected"})

    db = get_database_settings()
    engine = get_database_engine()
    configured = engine == "sqlite" or (
        bool(db.get("host")) and bool(db.get("name"))
    )
    if engine == "sqlite":
        from .sample_database import ensure_configured_sample_if_needed

        ensure_configured_sample_if_needed()
    if not configured:
        database: dict[str, Any] = {
            "status": "not_configured",
            "engine": engine,
            "detail": "Database connection is not configured",
        }
    else:
        try:
            with db_sql.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
            database = {"status": "connected", "engine": engine, "detail": ""}
        except Exception as exc:  # noqa: BLE001 — surface any driver/network error
            database = {
                "status": "disconnected",
                "engine": engine,
                "detail": str(exc),
            }

    if get_openrouter_token():
        openrouter: dict[str, Any] = {"status": "configured", "detail": ""}
    else:
        openrouter = {
            "status": "missing_token",
            "detail": "API key is not set",
        }

    if get_cursor_token():
        cursor: dict[str, Any] = {"status": "configured", "detail": ""}
    else:
        cursor = {
            "status": "missing_token",
            "detail": "Cursor API key is not set",
        }

    provider = get_provider()
    if provider == "cursor":
        install = detect_cursor_install()
        if not install.get("installed"):
            llm = {
                "status": "not_configured",
                "detail": install.get("detail")
                or (
                    "Cursor is not installed on this machine. "
                    "Install it from https://cursor.com then try again."
                ),
            }
        elif not get_cursor_token():
            llm = {
                "status": "missing_token",
                "detail": "Cursor API key is not set",
            }
        elif not get_llm_base_url():
            llm = {
                "status": "not_configured",
                "detail": "Cursor adapter base URL is not set",
            }
        else:
            llm = {"status": "configured", "detail": ""}
    elif not get_openrouter_token():
        llm = {"status": "missing_token", "detail": "API key is not set"}
    elif provider == "openai_compatible" and not get_llm_base_url():
        llm = {"status": "not_configured", "detail": "Base URL is not set"}
    else:
        llm = {"status": "configured", "detail": ""}

    ok = database.get("status") == "connected"
    return JsonResponse(
        {
            "ok": ok,
            "api": api,
            "database": stamp(database),
            "llm": stamp(llm),
            "openrouter": stamp(openrouter),
            "cursor": stamp(cursor),
            "provider": provider,
        }
    )


# --- Agents ---


@csrf_exempt
@require_http_methods(["GET", "PUT", "POST"])
def agents_list(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"agents": store.list_agents()})
    if request.method == "POST":
        try:
            body = _json_body(request)
        except ValueError as exc:
            return _error(str(exc))
        agent_id = body.get("id") or ""
        name = body.get("role") or body.get("name") or ""
        description = body.get("description") or ""
        try:
            created = create_custom_agent(
                str(agent_id),
                str(name),
                str(description) if description is not None else "",
            )
        except ValueError as exc:
            return _error(str(exc), 400)
        return JsonResponse(created, status=201)
    return _error("Bulk instruction updates are no longer supported", 410)


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def agent_instruction(request: HttpRequest, agent_id: str) -> JsonResponse:
    return _error("Agents use rules and skills only; instructions are removed", 410)


# --- References ---


@csrf_exempt
@require_http_methods(["GET", "POST"])
def references_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"references": store.list_references()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    name = body.get("name") or body.get("filename") or ""
    content = body.get("content", "")
    if not name:
        return _error("name is required")
    try:
        item = store.create_reference(str(name), content if isinstance(content, str) else "")
    except ValueError as exc:
        return _error(str(exc))
    except FileExistsError:
        return _error("Reference already exists", 409)
    return JsonResponse(item, status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def reference_detail(request: HttpRequest, name: str) -> HttpResponse:
    try:
        if request.method == "GET":
            return JsonResponse(store.get_reference(name))
        if request.method == "DELETE":
            store.delete_reference(name)
            return HttpResponse(status=204)
        body = _json_body(request)
        content = body.get("content", "")
        if not isinstance(content, str):
            return _error("content must be a string")
        return JsonResponse(store.update_reference(name, content))
    except ValueError as exc:
        return _error(str(exc))
    except FileNotFoundError:
        return _error("Reference not found", 404)


# --- Rules ---


@csrf_exempt
@require_http_methods(["GET", "POST"])
def rules_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"rules": store.list_rules()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    rule_id = body.get("id") or ""
    content = body.get("content", "")
    agents = body.get("agents")
    name = body.get("name")
    disabled = body.get("disabled")
    if not rule_id:
        return _error("id is required")
    try:
        item = store.create_rule(
            str(rule_id),
            content if isinstance(content, str) else "",
            agents if isinstance(agents, list) else None,
            name=str(name) if name is not None else None,
            disabled=bool(disabled),
        )
    except ValueError as exc:
        return _error(str(exc))
    except FileExistsError:
        return _error("Rule already exists", 409)
    return JsonResponse(item, status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def rules_assignments(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"assignments": store.load_assignments()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    assignments = body.get("assignments")
    if not isinstance(assignments, dict):
        return _error("assignments must be an object")
    saved = store.save_assignments(assignments)
    return JsonResponse({"assignments": saved})


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def skills_assignments(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"assignments": store.load_skill_assignments()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    assignments = body.get("assignments")
    if not isinstance(assignments, dict):
        return _error("assignments must be an object")
    saved = store.save_skill_assignments(assignments)
    return JsonResponse({"assignments": saved})


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def rule_detail(request: HttpRequest, rule_id: str) -> HttpResponse:
    try:
        if request.method == "GET":
            return JsonResponse(store.get_rule(rule_id))
        if request.method == "DELETE":
            store.delete_rule(rule_id)
            return HttpResponse(status=204)
        body = _json_body(request)
        content = body.get("content")
        agents = body.get("agents")
        name = body.get("name")
        disabled = body.get("disabled")
        if content is not None and not isinstance(content, str):
            return _error("content must be a string")
        if agents is not None and not isinstance(agents, list):
            return _error("agents must be a list")
        return JsonResponse(
            store.update_rule(
                rule_id,
                content=content,
                agents=agents,
                name=str(name) if name is not None else None,
                disabled=None if disabled is None else bool(disabled),
            )
        )
    except ValueError as exc:
        return _error(str(exc))
    except FileNotFoundError:
        return _error("Rule not found", 404)


# --- Skills ---


@csrf_exempt
@require_http_methods(["GET", "POST"])
def skills_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        scope = request.GET.get("scope") or None
        try:
            return JsonResponse({"skills": store.list_skills(scope)})
        except KeyError as exc:
            return _error(str(exc), 404)
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    skill_id = body.get("id") or ""
    scope = body.get("scope") or ""
    content = body.get("content", "")
    agents = body.get("agents")
    name = body.get("name")
    disabled = body.get("disabled")
    if not skill_id:
        return _error("id is required")
    try:
        item = store.create_skill(
            str(scope),
            str(skill_id),
            content if isinstance(content, str) else "",
            agents=agents if isinstance(agents, list) else None,
            name=str(name) if name is not None else None,
            disabled=bool(disabled),
        )
    except ValueError as exc:
        return _error(str(exc))
    except KeyError as exc:
        return _error(str(exc), 404)
    except FileExistsError:
        return _error("Skill already exists", 409)
    return JsonResponse(item, status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def skill_detail(request: HttpRequest, scope: str, skill_id: str) -> HttpResponse:
    try:
        if request.method == "GET":
            return JsonResponse(store.get_skill(scope, skill_id))
        if request.method == "DELETE":
            store.delete_skill(scope, skill_id)
            return HttpResponse(status=204)
        body = _json_body(request)
        content = body.get("content")
        agents = body.get("agents")
        name = body.get("name")
        disabled = body.get("disabled")
        if content is not None and not isinstance(content, str):
            return _error("content must be a string")
        if agents is not None and not isinstance(agents, list):
            return _error("agents must be a list")
        return JsonResponse(
            store.update_skill(
                scope,
                skill_id,
                content,
                agents=agents if isinstance(agents, list) else None,
                name=str(name) if name is not None else None,
                disabled=None if disabled is None else bool(disabled),
            )
        )
    except ValueError as exc:
        return _error(str(exc))
    except KeyError as exc:
        return _error(str(exc), 404)
    except FileNotFoundError:
        return _error("Skill not found", 404)


# --- Admin database ---


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def admin_database(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        db = get_database_settings()
        return JsonResponse(
            {
                "database": db,
                "connection_string": database_to_connection_string(db),
            }
        )
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    payload = body.get("database") if isinstance(body.get("database"), dict) else body
    if isinstance(body, dict) and "connection_string" in body and "connection_string" not in payload:
        payload = {**payload, "connection_string": body["connection_string"]}
    try:
        db = update_database_settings(payload)
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse(
        {
            "database": db,
            "connection_string": database_to_connection_string(db),
        }
    )


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def admin_openrouter(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"openrouter": get_openrouter_settings()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    payload = body.get("openrouter") if isinstance(body.get("openrouter"), dict) else body
    try:
        openrouter = update_openrouter_settings(payload)
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse({"openrouter": openrouter})


@csrf_exempt
@require_http_methods(["GET"])
def admin_openrouter_models(request: HttpRequest) -> JsonResponse:
    force = request.GET.get("force") in ("1", "true", "yes")
    try:
        models = fetch_openrouter_models(force=force)
    except ValueError as exc:
        message = str(exc)
        status = 400 if "is not set" in message else 502
        return _error(message, status=status)
    return JsonResponse({"models": models})




@csrf_exempt
@require_http_methods(["PATCH", "PUT", "DELETE"])
def agent_rename(request: HttpRequest, agent_id: str) -> JsonResponse:
    if agent_id not in known_agent_ids():
        return _error(f"Unknown agent: {agent_id}", 404)
    if request.method == "DELETE":
        try:
            delete_custom_agent(agent_id)
        except KeyError:
            return _error(f"Unknown agent: {agent_id}", 404)
        except ValueError as exc:
            return _error(str(exc), 400)
        return JsonResponse({"deleted": agent_id})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    name = body.get("role") if "role" in body else body.get("name")
    disabled = body.get("disabled")
    description = body.get("description")
    if name is not None:
        if not isinstance(name, str):
            return _error("name must be a string")
        try:
            update_agent_display_name(agent_id, name)
        except ValueError as exc:
            return _error(str(exc))
        except KeyError:
            return _error(f"Unknown agent: {agent_id}", 404)
    if disabled is not None:
        try:
            set_agent_disabled(agent_id, bool(disabled))
        except KeyError:
            return _error(f"Unknown agent: {agent_id}", 404)
    if description is not None:
        try:
            update_agent_fields(
                agent_id,
                description=str(description) if description is not None else None,
            )
        except ValueError as exc:
            return _error(str(exc))
        except KeyError:
            return _error(f"Unknown agent: {agent_id}", 404)
    try:
        meta = get_agent_meta(agent_id)
    except KeyError:
        return _error(f"Unknown agent: {agent_id}", 404)
    names = get_agent_display_names()
    meta = {**meta, "name": names.get(agent_id, meta.get("name"))}
    return JsonResponse(meta)


@csrf_exempt
@require_http_methods(["POST"])
def rule_rename(request: HttpRequest, rule_id: str) -> JsonResponse:
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    new_id = body.get("new_id") or body.get("name") or ""
    if not new_id:
        return _error("new_id is required")
    try:
        item = store.rename_rule(rule_id, str(new_id))
    except ValueError as exc:
        return _error(str(exc))
    except FileNotFoundError:
        return _error("Rule not found", 404)
    except FileExistsError:
        return _error("A rule with that id already exists", 409)
    return JsonResponse(item)


@csrf_exempt
@require_http_methods(["POST"])
def skill_rename(request: HttpRequest, scope: str, skill_id: str) -> JsonResponse:
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    new_id = body.get("new_id") or body.get("name") or ""
    if not new_id:
        return _error("new_id is required")
    try:
        item = store.rename_skill(scope, skill_id, str(new_id))
    except ValueError as exc:
        return _error(str(exc))
    except KeyError as exc:
        return _error(str(exc), 404)
    except FileNotFoundError:
        return _error("Skill not found", 404)
    except FileExistsError:
        return _error("A skill with that id already exists", 409)
    return JsonResponse(item)


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def admin_provider(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse(get_active_provider_settings())
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    provider = body.get("provider")
    if not isinstance(provider, str):
        return _error("provider must be a string")
    try:
        saved = update_provider(provider)
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse(get_active_provider_settings() | {"provider": saved})


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def admin_cursor(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"cursor": get_cursor_settings()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    payload = body.get("cursor") if isinstance(body.get("cursor"), dict) else body
    try:
        cursor = update_cursor_settings(payload)
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse({"cursor": cursor})


@csrf_exempt
@require_http_methods(["GET"])
def admin_cursor_models(request: HttpRequest) -> JsonResponse:
    force = request.GET.get("force") in ("1", "true", "yes")
    try:
        models = fetch_cursor_models(force=force)
    except ValueError as exc:
        message = str(exc)
        status = 400 if "is not set" in message else 502
        return _error(message, status=status)
    return JsonResponse({"models": models})


@csrf_exempt
@require_http_methods(["GET"])
def admin_cursor_install_status(request: HttpRequest) -> JsonResponse:
    return JsonResponse(detect_cursor_install())


@csrf_exempt
@require_http_methods(["GET"])
def docs_tables(request: HttpRequest) -> JsonResponse:
    return JsonResponse(docs_catalog.list_docs_tables())


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def docs_table_detail(request: HttpRequest, table: str) -> JsonResponse:
    try:
        if request.method == "GET":
            return JsonResponse(docs_catalog.get_table_docs(table))
        body = _json_body(request)
        if "column" in body:
            column = body.get("column")
            description = body.get("description", "")
            sql_description = body.get("sql_description", "")
            if not isinstance(column, str) or not column.strip():
                return _error("column must be a string")
            if not isinstance(description, str):
                return _error("description must be a string")
            if not isinstance(sql_description, str):
                return _error("sql_description must be a string")
            return JsonResponse(
                docs_catalog.update_column_docs(
                    table, column, description, sql_description
                )
            )
        overview = body.get("overview", "")
        if not isinstance(overview, str):
            return _error("overview must be a string")
        return JsonResponse(docs_catalog.update_table_overview(table, overview))
    except ValueError as exc:
        return _error(str(exc))
    except FileNotFoundError:
        return _error("tables.md not found", 404)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def results_collection(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"results": results_store.list_results()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    prompt = body.get("prompt") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return _error("prompt is required")
    mode = body.get("mode") or "auto"
    language = body.get("language") or "en"
    if not isinstance(mode, str) or not isinstance(language, str):
        return _error("mode and language must be strings")
    payload = body.get("payload")
    item = results_store.create_result(
        prompt=prompt.strip(),
        mode=mode,
        language=language,
        payload=payload,
        duration_s=body.get("duration_s"),
    )
    return JsonResponse(item, status=201)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def results_detail(request: HttpRequest, result_id: str) -> HttpResponse:
    try:
        if request.method == "GET":
            return JsonResponse(results_store.get_result(result_id))
        if request.method == "DELETE":
            results_store.delete_result(result_id)
            return HttpResponse(status=204)
        body = _json_body(request)
        if "archived" not in body:
            return _error("archived is required")
        if not isinstance(body.get("archived"), bool):
            return _error("archived must be a boolean")
        return JsonResponse(
            results_store.update_result(result_id, archived=body["archived"])
        )
    except ValueError as exc:
        return _error(str(exc))
    except KeyError:
        return _error("Result not found", 404)


@csrf_exempt
@require_http_methods(["GET"])
def logs_collection(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"logs": logs_store.list_logs()})


@csrf_exempt
@require_http_methods(["GET", "DELETE"])
def logs_detail(request: HttpRequest, log_id: str) -> HttpResponse:
    try:
        if request.method == "GET":
            return JsonResponse(logs_store.get_log(log_id))
        logs_store.delete_log(log_id)
        return HttpResponse(status=204)
    except KeyError:
        return _error("Log not found", 404)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def db_explorer_query(request: HttpRequest) -> JsonResponse:
    try:
        if request.method == "GET":
            payload = {
                "table": request.GET.get("table") or "",
                "limit": request.GET.get("limit") or 32,
                "position": request.GET.get("position") or "top",
                "where": request.GET.get("where") or "",
                "order_by": request.GET.get("order_by") or "",
                "sort": request.GET.get("sort") or "ASC",
            }
        else:
            payload = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))

    try:
        limit = int(payload.get("limit") or 32)
    except (TypeError, ValueError):
        return _error("limit must be an integer")

    try:
        result = db_sql.select_rows(
            table=str(payload.get("table") or ""),
            limit=limit,
            position=str(payload.get("position") or "top"),
            where=str(payload.get("where") or ""),
            order_by=str(payload.get("order_by") or ""),
            sort=str(payload.get("sort") or "ASC"),
        )
    except ValueError as exc:
        _record_log_error(
            kind="sql",
            message=str(exc),
            path="/api/db-explorer/query/",
            status_code=400,
        )
        return _error(str(exc))
    except Exception as exc:  # noqa: BLE001
        _record_log_error(
            kind="sql",
            message=str(exc),
            path="/api/db-explorer/query/",
            status_code=502,
        )
        return _error(str(exc), 502)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
def db_explorer_tables(request: HttpRequest) -> JsonResponse:
    try:
        tables = db_sql.list_tables()
    except ValueError as exc:
        return _error(str(exc), 503)
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 502)
    return JsonResponse({"tables": tables})


@csrf_exempt
@require_http_methods(["GET"])
def db_explorer_columns(request: HttpRequest) -> JsonResponse:
    table = request.GET.get("table") or ""
    try:
        schema, name = db_sql.parse_table_name(table)
        columns = db_sql.list_columns(schema, name)
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc), 502)
    return JsonResponse({"table": f"{schema}.{name}", "columns": columns})


# --- Admin pipeline graph ---


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def admin_pipeline_graph(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse(get_pipeline_bundle())
    if request.method == "DELETE":
        return JsonResponse(reset_pipeline_bundle())
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    payload = body if isinstance(body, dict) else {}
    try:
        bundle = update_pipeline_bundle(payload)
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse(bundle)


# --- Run SSE ---


def _parse_run_options(
    body: dict[str, Any],
) -> (
    tuple[str, str, str, str | None, str | None, list[str] | None, list[str] | None]
    | JsonResponse
):
    prompt = (body.get("prompt") or "").strip()
    mode = body.get("mode") or "auto"
    language = body.get("language") or "en"
    report_type = body.get("report_type") or None
    chart_type = body.get("chart_type") or None
    raw_chart_types = body.get("chart_types")
    raw_columns = body.get("columns")

    if mode not in VALID_MODES:
        return _error(
            "mode must be auto, chart, grid, research, analytical_report, or analytical_report_chart"
        )
    if language not in VALID_LANGUAGES:
        return _error("language must be en or fa")
    if not prompt:
        return _error("prompt is required")
    if report_type is not None and report_type not in VALID_REPORT_TYPES:
        return _error("report_type must be low, medium, or high")
    if chart_type is not None and chart_type not in VALID_CHART_TYPES:
        return _error("chart_type is invalid")

    chart_types: list[str] | None = None
    if isinstance(raw_chart_types, list):
        chart_types = []
        for item in raw_chart_types:
            value = str(item or "").strip()
            if value not in VALID_CHART_TYPES:
                return _error("chart_types contains an invalid chart type")
            if value not in chart_types:
                chart_types.append(value)
            if len(chart_types) >= 4:
                break
        if not chart_types:
            chart_types = None
    if chart_types and not chart_type:
        chart_type = chart_types[0]
    elif chart_type and not chart_types:
        chart_types = [chart_type]

    columns: list[str] | None = None
    if isinstance(raw_columns, list):
        columns = [str(c).strip() for c in raw_columns if str(c).strip()]
    elif isinstance(raw_columns, str) and raw_columns.strip():
        columns = [
            p.strip()
            for p in raw_columns.replace("،", ",").replace("/", ",").split(",")
            if p.strip()
        ]

    return prompt, mode, language, report_type, chart_type, chart_types, columns


def _resolve_actor(body: dict[str, Any]) -> dict[str, Any]:
    username = str(body.get("username") or body.get("user") or "").strip().lower()
    if not username:
        return {"username": "guest", "is_admin": False, "is_guest": True}
    for user in org.list_users():
        if user["username"] == username or user["id"] == username:
            return {
                "id": user["id"],
                "username": user["username"],
                "is_admin": bool(user["is_admin"]),
                "allowed_tables": list(user.get("allowed_tables") or []),
                "data_access_plain": str(user.get("data_access_plain") or ""),
            }
    return {"username": username, "is_admin": False, "unknown": True}


@csrf_exempt
@require_http_methods(["POST"])
def runs_stream(request: HttpRequest) -> HttpResponse:
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))

    parsed = _parse_run_options(body)
    if isinstance(parsed, JsonResponse):
        return parsed
    prompt, mode, language, report_type, chart_type, chart_types, columns = parsed
    actor = _resolve_actor(body)

    try:
        require_llm()
    except ValueError as exc:
        _record_log_error(
            kind="llm",
            message=str(exc),
            prompt=prompt,
            mode=mode,
            language=language,
            path="/api/runs/stream",
            status_code=400,
        )
        return _error(str(exc), 400)
    import json as _agent_json
    import time as _agent_time
    import urllib.request as _agent_urllib

    _payload_604 = _agent_json.dumps(
        {
            "sessionId": "604d40",
            "timestamp": int(_agent_time.time() * 1000),
            "location": "views.py:runs_stream",
            "message": "Stream request accepted",
            "data": {
                "mode": mode,
                "language": language,
                "prompt_len": len(prompt),
            },
            "hypothesisId": "G",
            "runId": "post-fix",
        }
    )
    for _path_604 in (
        r"C:\Users\armin\GitHub\helix-webui\debug-604d40.log",
        r"C:\Users\armin\GitHub\helix-webui\.cursor\debug-604d40.log",
        r"C:\Users\armin\GitHub\helix-api\debug-604d40.log",
    ):
        try:
            with open(_path_604, "a", encoding="utf-8") as _dbg604:
                _dbg604.write(_payload_604 + "\n")
        except Exception:
            pass
    try:
        _agent_urllib.urlopen(
            _agent_urllib.Request(
                "http://127.0.0.1:7706/ingest/ac544aa8-f980-4348-bd8e-331cdfbc33b6",
                data=_payload_604.encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Debug-Session-Id": "604d40",
                },
                method="POST",
            ),
            timeout=2,
        ).read()
    except Exception:
        pass
    try:
        with open(
            r"C:\Users\armin\GitHub\helix-api\debug-9f5f92.log",
            "a",
            encoding="utf-8",
        ) as _agent_log:
            _agent_log.write(
                _agent_json.dumps(
                    {
                        "sessionId": "9f5f92",
                        "timestamp": int(_agent_time.time() * 1000),
                        "location": "views.py:runs_stream",
                        "message": "Stream request accepted",
                        "data": {
                            "mode": mode,
                            "language": language,
                            "prompt_len": len(prompt),
                        },
                        "hypothesisId": "B",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

    response = StreamingHttpResponse(
        pipeline_events(
            prompt,
            mode,
            language=language,
            report_type=report_type,
            chart_type=chart_type,
            chart_types=chart_types,
            columns=columns,
            actor=actor,
        ),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@csrf_exempt
@require_http_methods(["POST"])
def chat(request: HttpRequest) -> JsonResponse:
    """Non-streaming compatibility endpoint."""
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))

    parsed = _parse_run_options(body)
    if isinstance(parsed, JsonResponse):
        return parsed
    prompt, mode, language, report_type, chart_type, chart_types, columns = parsed
    actor = _resolve_actor(body)
    try:
        require_llm()
    except ValueError as exc:
        _record_log_error(
            kind="llm",
            message=str(exc),
            prompt=prompt,
            mode=mode,
            language=language,
            path="/api/chat",
            status_code=400,
        )
        return _error(str(exc), 400)
    try:
        result = run_pipeline_sync(
            prompt,
            mode,
            language=language,
            report_type=report_type,
            chart_type=chart_type,
            chart_types=chart_types,
            columns=columns,
            actor=actor,
        )
    except ValueError as exc:
        message = str(exc)
        lowered = message.lower()
        if (
            lowered.startswith("llm ")
            or "llm request" in lowered
            or "llm returned" in lowered
            or "sql server closed" in lowered
            or "pyodbc" in lowered
            or "exception set" in lowered
            or "08s01" in lowered
            or "communication link" in lowered
        ):
            return _error(message, 502)
        return _error(message, 400)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
def sample_tiers(request: HttpRequest) -> JsonResponse:
    from .sample_database import list_sample_tiers

    return JsonResponse({"tiers": list_sample_tiers()})


@csrf_exempt
@require_http_methods(["POST"])
def sample_tier_ensure(request: HttpRequest, tier_id: str) -> JsonResponse:
    from .sample_database import ensure_sample_tier

    try:
        body = _json_body(request) if request.body else {}
    except ValueError:
        body = {}
    force = bool(body.get("force")) if isinstance(body, dict) else False
    try:
        item = ensure_sample_tier(tier_id, force=force)
    except KeyError:
        return _error(f"Unknown sample tier: {tier_id}", 404)
    except Exception as exc:
        return _error(str(exc), 500)
    return JsonResponse(item)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def admin_users(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"users": org.list_users()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    from .access_policy import review_data_access_policy

    is_admin = bool(body.get("is_admin"))
    plain = str(body.get("data_access_plain") or "")
    review = review_data_access_policy(plain, is_admin=is_admin)
    if not review.get("accepted"):
        return _error(str(review.get("message") or "Guardian rejected data access"), 400)
    try:
        item = org.create_user(
            str(body.get("username") or ""),
            str(body.get("display_name") or ""),
            is_admin=is_admin,
            data_access_plain=str(review.get("data_access_plain") or plain),
            allowed_tables=list(review.get("allowed_tables") or []),
        )
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse(item, status=201)


@csrf_exempt
@require_http_methods(["PUT", "PATCH", "DELETE"])
def admin_user_detail(request: HttpRequest, user_id: str) -> JsonResponse:
    if request.method == "DELETE":
        try:
            org.delete_user(user_id)
        except KeyError:
            return _error(f"Unknown user: {user_id}", 404)
        except ValueError as exc:
            return _error(str(exc))
        return JsonResponse({"deleted": user_id})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    if "data_access_plain" in body or "allowed_tables" in body:
        from .access_policy import review_data_access_policy

        try:
            existing = org.get_user(user_id)
        except KeyError:
            return _error(f"Unknown user: {user_id}", 404)
        is_admin = (
            bool(body["is_admin"])
            if "is_admin" in body and body["is_admin"] is not None
            else bool(existing.get("is_admin"))
        )
        plain = (
            str(body.get("data_access_plain"))
            if "data_access_plain" in body
            else str(existing.get("data_access_plain") or "")
        )
        review = review_data_access_policy(plain, is_admin=is_admin)
        if not review.get("accepted"):
            return _error(
                str(review.get("message") or "Guardian rejected data access"), 400
            )
        body = {
            **body,
            "data_access_plain": review.get("data_access_plain") or plain,
            "allowed_tables": list(review.get("allowed_tables") or []),
        }
    try:
        item = org.update_user(user_id, body)
    except KeyError:
        return _error(f"Unknown user: {user_id}", 404)
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse(item)
