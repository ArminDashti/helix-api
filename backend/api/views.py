"""HTTP views for Helix API."""

from __future__ import annotations

import json
import time
from typing import Any, Iterator

from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import markdown_store as store
from .agents import AGENT_BY_ID, AGENT_PIPELINE
from .config_loader import (
    database_to_connection_string,
    get_database_settings,
    get_openrouter_settings,
    update_database_settings,
    update_openrouter_settings,
)
from .demo import get_demo_result


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


# --- Agents / instructions ---


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def agents_list(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse({"agents": store.list_agents_with_instructions()})
    # PUT bulk update: { "instructions": { "task_validator": "..." } }
    try:
        body = _json_body(request)
    except ValueError as exc:
        return _error(str(exc))
    instructions = body.get("instructions") or {}
    if not isinstance(instructions, dict):
        return _error("instructions must be an object")
    updated = []
    for agent_id, content in instructions.items():
        if agent_id not in AGENT_BY_ID:
            return _error(f"Unknown agent: {agent_id}")
        store.set_instruction(agent_id, content if isinstance(content, str) else str(content))
        updated.append(agent_id)
    return JsonResponse({"updated": updated, "agents": store.list_agents_with_instructions()})


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def agent_instruction(request: HttpRequest, agent_id: str) -> JsonResponse:
    if agent_id not in AGENT_BY_ID:
        return _error(f"Unknown agent: {agent_id}", 404)
    if request.method == "GET":
        return JsonResponse(
            {
                **AGENT_BY_ID[agent_id],
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
    return JsonResponse({**AGENT_BY_ID[agent_id], "instruction": saved})


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


# --- Run SSE ---


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _pipeline_events(prompt: str, mode: str) -> Iterator[str]:
    """Emit consecutive step events, then a demo result."""
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
            "message": f"Received prompt ({mode}): {prompt[:120]}",
        }
    )
    time.sleep(0.25)

    for meta in AGENT_PIPELINE:
        agent_id = meta["id"]
        yield _sse(
            {
                "event": "step",
                "agent_id": agent_id,
                "status": "running",
                "message": messages.get(agent_id, meta["description"]),
            }
        )
        time.sleep(delay)

        # Stub one retry loop for sql_guardian (visual loop edge)
        if agent_id == "sql_guardian":
            yield _sse(
                {
                    "event": "step",
                    "agent_id": agent_id,
                    "status": "retry",
                    "message": "Minor SQL tweak requested — sending back to Code Builder…",
                    "retry_to": "code_builder",
                }
            )
            time.sleep(delay * 0.7)
            yield _sse(
                {
                    "event": "step",
                    "agent_id": "code_builder",
                    "status": "running",
                    "message": "Adjusting SQL after guardian feedback…",
                }
            )
            time.sleep(delay * 0.6)
            yield _sse(
                {
                    "event": "step",
                    "agent_id": "code_builder",
                    "status": "done",
                    "message": "SQL revised",
                }
            )
            time.sleep(0.3)
            yield _sse(
                {
                    "event": "step",
                    "agent_id": "sql_guardian",
                    "status": "running",
                    "message": "Re-checking revised SQL…",
                }
            )
            time.sleep(delay * 0.5)

        yield _sse(
            {
                "event": "step",
                "agent_id": agent_id,
                "status": "done",
                "message": f"{meta['name']} complete",
            }
        )
        time.sleep(0.2)

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
