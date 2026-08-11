"""HTTP views for Helix API."""

from __future__ import annotations

import json
import time
from typing import Any, Iterator

from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import markdown_store as store
from . import db_sql
from . import docs_catalog
from .config_loader import (
    create_custom_agent,
    database_to_connection_string,
    delete_custom_agent,
    fetch_cursor_models,
    fetch_openrouter_models,
    get_active_provider_settings,
    get_agent_display_names,
    get_agent_meta,
    get_cursor_settings,
    get_cursor_token,
    get_database_settings,
    get_openrouter_settings,
    get_openrouter_token,
    get_provider,
    known_agent_ids,
    update_agent_display_name,
    update_cursor_settings,
    update_database_settings,
    update_openrouter_settings,
    update_provider,
)
from .agents import is_builtin_agent
from .demo import get_demo_result
from .pipeline_graph import (
    MAX_STEPS,
    MAX_VISITS_PER_NODE,
    agent_display_name,
    get_pipeline_graph,
    next_targets,
    reset_pipeline_graph,
    update_pipeline_graph,
)


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


# --- Health / connectivity ---


@csrf_exempt
@require_http_methods(["GET"])
def health(request: HttpRequest) -> JsonResponse:
    """Report connectivity for helix-api, SQL database, and LLM providers."""
    api = {"status": "connected"}

    db = get_database_settings()
    if not db.get("host") or not db.get("name"):
        database: dict[str, Any] = {
            "status": "not_configured",
            "detail": "Host and database name are not set",
        }
    else:
        try:
            with db_sql.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
            database = {"status": "connected"}
        except Exception as exc:  # noqa: BLE001 — surface any driver/network error
            database = {"status": "disconnected", "detail": str(exc)}

    if get_openrouter_token():
        openrouter: dict[str, Any] = {"status": "configured"}
    else:
        openrouter = {
            "status": "missing_token",
            "detail": "OPENROUTER_TOKEN is not set",
        }

    if get_cursor_token():
        cursor: dict[str, Any] = {"status": "configured"}
    else:
        cursor = {
            "status": "missing_token",
            "detail": "CURSOR_API_KEY is not set",
        }

    ok = database.get("status") == "connected"
    return JsonResponse(
        {
            "ok": ok,
            "api": api,
            "database": database,
            "openrouter": openrouter,
            "cursor": cursor,
        }
    )


# --- Agents / instructions ---


@csrf_exempt
@require_http_methods(["GET", "PUT", "POST"])
def agents_list(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"agents": store.list_agents_with_instructions()})
    if request.method == "POST":
        try:
            body = _json_body(request)
        except ValueError as exc:
            return _error(str(exc))
        agent_id = body.get("id") or ""
        name = body.get("name") or ""
        description = body.get("description") or ""
        instruction = body.get("instruction", "")
        try:
            created = create_custom_agent(
                str(agent_id),
                str(name),
                str(description) if description is not None else "",
                instruction=instruction if isinstance(instruction, str) else str(instruction or ""),
            )
        except ValueError as exc:
            return _error(str(exc), 400)
        return JsonResponse(created, status=201)
    # PUT bulk update: { "instructions": { "task_validator": "..." } }
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    instructions = body.get("instructions") or {}
    if not isinstance(instructions, dict):
        return _error("instructions must be an object")
    known = known_agent_ids()
    updated = []
    for agent_id, content in instructions.items():
        if agent_id not in known:
            return _error(f"Unknown agent: {agent_id}")
        store.set_instruction(agent_id, content if isinstance(content, str) else str(content))
        updated.append(agent_id)
    return JsonResponse({"updated": updated, "agents": store.list_agents_with_instructions()})


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def agent_instruction(request: HttpRequest, agent_id: str) -> JsonResponse:
    known = known_agent_ids()
    if agent_id not in known:
        return _error(f"Unknown agent: {agent_id}", 404)
    try:
        meta = get_agent_meta(agent_id)
    except KeyError:
        return _error(f"Unknown agent: {agent_id}", 404)
    if request.method == "GET":
        names = get_agent_display_names()
        return JsonResponse(
            {
                **meta,
                "name": names.get(agent_id, meta["name"]),
                "instruction": store.get_instruction(agent_id),
            }
        )
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    content = body.get("instruction", body.get("content", ""))
    if content is None:
        content = ""
    if not isinstance(content, str):
        return _error("instruction must be a string")
    saved = store.set_instruction(agent_id, content)
    return JsonResponse({**meta, "instruction": saved})


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
    rule_id = body.get("id") or body.get("name") or ""
    content = body.get("content", "")
    agents = body.get("agents")
    if not rule_id:
        return _error("id is required")
    try:
        item = store.create_rule(
            str(rule_id),
            content if isinstance(content, str) else "",
            agents if isinstance(agents, list) else None,
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
        if content is not None and not isinstance(content, str):
            return _error("content must be a string")
        if agents is not None and not isinstance(agents, list):
            return _error("agents must be a list")
        return JsonResponse(
            store.update_rule(
                rule_id,
                content=content,
                agents=agents,
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
    skill_id = body.get("id") or body.get("name") or ""
    scope = body.get("scope") or ""
    content = body.get("content", "")
    if not skill_id:
        return _error("id is required")
    if not scope:
        return _error("scope is required (shared or an agent id)")
    try:
        item = store.create_skill(
            str(scope),
            str(skill_id),
            content if isinstance(content, str) else "",
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
        content = body.get("content", "")
        if not isinstance(content, str):
            return _error("content must be a string")
        return JsonResponse(store.update_skill(scope, skill_id, content))
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
        status = 503 if "OPENROUTER_TOKEN" in message else 502
        return _error(message, status=status)
    return JsonResponse({"models": models})




@csrf_exempt
@require_http_methods(["PATCH", "PUT", "DELETE"])
def agent_rename(request: HttpRequest, agent_id: str) -> JsonResponse:
    if agent_id not in known_agent_ids():
        return _error(f"Unknown agent: {agent_id}", 404)
    if request.method == "DELETE":
        if is_builtin_agent(agent_id):
            return _error("Cannot delete a built-in pipeline agent", 400)
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
    name = body.get("name")
    if not isinstance(name, str):
        return _error("name must be a string")
    try:
        names = update_agent_display_name(agent_id, name)
    except ValueError as exc:
        return _error(str(exc))
    except KeyError:
        return _error(f"Unknown agent: {agent_id}", 404)
    try:
        meta = get_agent_meta(agent_id)
    except KeyError:
        return _error(f"Unknown agent: {agent_id}", 404)
    meta = {**meta, "name": names[agent_id]}
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
        status = 503 if "CURSOR_API_KEY" in message else 502
        return _error(message, status=status)
    return JsonResponse({"models": models})


@csrf_exempt
@require_http_methods(["GET"])
def docs_tables(request: HttpRequest) -> JsonResponse:
    return JsonResponse(docs_catalog.list_docs_tables())


@csrf_exempt
@require_http_methods(["GET"])
def docs_table_detail(request: HttpRequest, table: str) -> JsonResponse:
    try:
        return JsonResponse(docs_catalog.get_table_docs(table))
    except ValueError as exc:
        return _error(str(exc))


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
        return _error(str(exc))
    except Exception as exc:  # noqa: BLE001
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
        return JsonResponse({"pipeline_graph": get_pipeline_graph()})
    if request.method == "DELETE":
        return JsonResponse({"pipeline_graph": reset_pipeline_graph()})
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    payload = (
        body.get("pipeline_graph")
        if isinstance(body.get("pipeline_graph"), dict)
        else body
    )
    try:
        graph = update_pipeline_graph(payload if isinstance(payload, dict) else {})
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse({"pipeline_graph": graph})


# --- Run SSE ---


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _pipeline_events(prompt: str, mode: str) -> Iterator[str]:
    """Walk the configured conditional DAG and emit step/result SSE events."""
    provider = get_provider()
    graph = get_pipeline_graph()
    delay = 0.55
    messages = {
        "task_validator": "Checking prompt feasibility and mode…",
        "solution_strategist": "Drafting a non-technical solution narrative…",
        "technical_architect": "Building the technical blueprint…",
        "code_builder": "Implementing sandbox analysis code…",
        "sql_guardian": "Reviewing SQL for safety and allowlist compliance…",
        "implementation_auditor": "Auditing implementation against the blueprint…",
        "response_publisher": "Packaging chart and report for the UI…",
    }

    yield _sse(
        {
            "event": "step",
            "agent_id": "user",
            "status": "done",
            "message": f"Received prompt ({mode}) via {provider}: {prompt[:120]}",
        }
    )
    time.sleep(0.25)

    entry = graph.get("entry")
    if not entry:
        result = get_demo_result(mode)
        yield _sse({"event": "result", **result, "used_demo": True})
        return

    visits: dict[str, int] = {}
    current: str | None = entry
    steps = 0

    while current and steps < MAX_STEPS:
        steps += 1
        visits[current] = visits.get(current, 0) + 1
        if visits[current] > MAX_VISITS_PER_NODE:
            yield _sse(
                {
                    "event": "step",
                    "agent_id": current,
                    "status": "failed",
                    "message": f"Visit cap reached for {current}",
                }
            )
            break

        display = agent_display_name(current)
        yield _sse(
            {
                "event": "step",
                "agent_id": current,
                "status": "running",
                "message": messages.get(current, f"Running {display}…"),
            }
        )
        time.sleep(delay)

        # Demo stub: sql_guardian emits one retry on first visit only
        if current == "sql_guardian" and visits[current] == 1:
            retry_targets = next_targets(graph, current, "retry")
            if retry_targets:
                yield _sse(
                    {
                        "event": "step",
                        "agent_id": current,
                        "status": "retry",
                        "message": "Minor SQL tweak requested — following retry edge…",
                        "retry_to": retry_targets[0],
                    }
                )
                time.sleep(delay * 0.5)
                current = retry_targets[0]
                continue

        yield _sse(
            {
                "event": "step",
                "agent_id": current,
                "status": "done",
                "message": f"{display} complete",
            }
        )
        time.sleep(0.2)

        targets = next_targets(graph, current, "done")
        current = targets[0] if targets else None

    result = get_demo_result(mode)
    yield _sse({"event": "result", **result, "used_demo": True})


@csrf_exempt
@require_http_methods(["POST"])
def runs_stream(request: HttpRequest) -> HttpResponse:
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))

    prompt = (body.get("prompt") or "").strip()
    mode = body.get("mode") or "both"
    if mode not in ("analysis", "chart", "both"):
        return _error("mode must be analysis, chart, or both")
    if not prompt:
        return _error("prompt is required")

    response = StreamingHttpResponse(
        _pipeline_events(prompt, mode),
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
    prompt = (body.get("prompt") or "").strip()
    mode = body.get("mode") or "both"
    if not prompt:
        return _error("prompt is required")
    if mode not in ("analysis", "chart", "both"):
        return _error("mode must be analysis, chart, or both")
    result = get_demo_result(mode)
    return JsonResponse({**result, "used_demo": True})
