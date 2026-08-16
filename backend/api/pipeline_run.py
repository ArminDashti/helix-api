"""Walk the arranged pipeline and produce a real report payload."""

from __future__ import annotations

import json
from typing import Any, Iterator

from . import markdown_store as store
from .chart_payload import build_echarts_option, build_grid
from .config_loader import get_provider
from .llm_client import complete_chat, parse_json_object, require_llm
from .pipeline_graph import (
    MAX_STEPS,
    agent_display_name,
    circuit_open_edge,
    edge_limit,
    get_pipeline_graph,
    next_edge,
)
from .sql_execute import execute_select, extract_sql


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _context_blob(ctx: dict[str, Any]) -> str:
    slim = {
        "prompt": ctx.get("prompt"),
        "mode": ctx.get("mode"),
        "language": ctx.get("language"),
        "report_type": ctx.get("report_type"),
        "chart_type": ctx.get("chart_type"),
        "columns": ctx.get("columns"),
        "artifacts": ctx.get("artifacts") or {},
        "sql_fetch": None,
    }
    fetch = ctx.get("sql_fetch")
    if isinstance(fetch, dict):
        rows = fetch.get("rows") or []
        slim["sql_fetch"] = {
            "sql": fetch.get("sql"),
            "columns": fetch.get("columns"),
            "row_count": len(rows),
            "preview": rows[:20],
        }
    return json.dumps(slim, ensure_ascii=False, default=str)


def _run_agent(agent_id: str, ctx: dict[str, Any]) -> tuple[str, str]:
    system = store.assemble_agent_prompt(agent_id)
    user = (
        "Use only the rules and skills above. "
        "Reply with a JSON object that includes result (string) and message (string). "
        f"Run context:\n{_context_blob(ctx)}"
    )
    if agent_id == "sql":
        user += (
            "\nAlso include a sql field with one SELECT for the warehouse. "
            "Do not invent numbers; the server will execute the SQL."
        )
    elif agent_id == "implementation_auditor":
        user += (
            "\nSet result to pass or fail. Check the work against the Technical Architect "
            "blueprint in artifacts.technical_architect when that blueprint exists. "
            "Pass when sql_fetch exists and the SQL matches the user request (allowlisted objects, "
            "SELECT-only, TOP/row bound). "
            "If there is no architect blueprint, still pass when sql_fetch rows match the asked table. "
            "Do not fail because text_report or echarts_option are missing from this context; "
            "the server builds those after SQL from sql_fetch."
        )
    elif agent_id == "response_publisher":
        user += (
            "\nWrite text_report from the sql_fetch preview numbers. "
            "Do not invent figures that are not in the preview."
        )

    raw = complete_chat(agent_id, user, system)
    parsed = parse_json_object(raw)
    message = str(parsed.get("message") or parsed.get("text") or raw).strip()
    result = str(parsed.get("result") or "done").strip().lower()

    if agent_id == "sql":
        sql_text = str(parsed.get("sql") or extract_sql(raw) or "")
        fetch = execute_select(sql_text)
        ctx["sql_fetch"] = fetch
        ctx.setdefault("artifacts", {})[agent_id] = {
            "sql": fetch["sql"],
            "row_count": len(fetch["rows"]),
            "message": message,
        }
        return "done", message or f"Fetched {len(fetch['rows'])} rows"

    artifacts = ctx.setdefault("artifacts", {})
    artifacts[agent_id] = {
        "message": message,
        "text": parsed.get("text_report") or parsed.get("text") or message,
    }
    if agent_id == "response_publisher" and parsed.get("text_report"):
        ctx["text_report"] = str(parsed.get("text_report"))
    if agent_id == "implementation_auditor":
        if result in ("pass", "done", "success"):
            return "pass", message or "Blueprint matched"
        return "fail", message or "Blueprint not matched"
    if result in ("failed", "fail", "error", "failure"):
        return "failed", message
    return "done", message or f"{agent_display_name(agent_id)} complete"


def _package_result(ctx: dict[str, Any]) -> dict[str, Any]:
    from .demo import VALID_CHART_TYPES

    mode = ctx.get("mode") or "auto"
    language = ctx.get("language") or "en"
    chart_type = ctx.get("chart_type") or "bar"
    if chart_type not in VALID_CHART_TYPES:
        chart_type = "bar"
    fetch = ctx.get("sql_fetch") if isinstance(ctx.get("sql_fetch"), dict) else None
    text_report = ctx.get("text_report")
    if not text_report:
        pub = (ctx.get("artifacts") or {}).get("response_publisher") or {}
        text_report = pub.get("text")
    if not text_report and fetch:
        count = len(fetch.get("rows") or [])
        text_report = (
            f"Query returned {count} rows."
            if language != "fa"
            else f"پرس‌وجو {count} ردیف برگرداند."
        )
    echarts_option = None
    grid = None
    if fetch:
        if mode in ("chart", "analytical_report_chart", "auto"):
            echarts_option = build_echarts_option(
                fetch, chart_type=chart_type, language=language
            )
        if mode in ("grid", "auto", "analytical_report_chart"):
            grid = build_grid(fetch, ctx.get("columns"))
        if mode == "analytical_report":
            grid = None
            echarts_option = None
        if mode == "chart":
            text_report = None
        if mode == "grid":
            text_report = None
            echarts_option = None
    if mode in ("analytical_report", "analytical_report_chart", "auto") and not text_report:
        raise ValueError("No report text was produced from the query results")
    if mode in ("chart", "analytical_report_chart", "auto") and not echarts_option and mode != "analytical_report":
        if mode in ("chart", "analytical_report_chart"):
            raise ValueError("No chart could be built from the query results")
    return {
        "mode": mode,
        "language": language,
        "report_type": ctx.get("report_type"),
        "chart_type": chart_type if echarts_option else None,
        "text_report": text_report,
        "echarts_option": echarts_option,
        "grid": grid,
        "used_demo": False,
    }


def pipeline_events(
    prompt: str,
    mode: str,
    *,
    language: str = "en",
    report_type: str | None = None,
    chart_type: str | None = None,
    columns: list[str] | None = None,
) -> Iterator[str]:
    try:
        require_llm()
    except ValueError as exc:
        yield _sse({"event": "error", "error": str(exc)})
        return

    provider = get_provider()
    graph = get_pipeline_graph()
    ctx: dict[str, Any] = {
        "prompt": prompt,
        "mode": mode,
        "language": language,
        "report_type": report_type,
        "chart_type": chart_type,
        "columns": columns,
        "artifacts": {},
    }

    yield _sse(
        {
            "event": "step",
            "agent_id": "user",
            "status": "done",
            "message": f"Received prompt ({mode}/{language}) via {provider}: {prompt[:120]}",
        }
    )

    entry = graph.get("entry")
    if not entry:
        raise ValueError("Pipeline has no entry agent")

    edge_uses: dict[str, int] = {}
    current: str | None = str(entry)
    steps = 0

    def pick_next(source: str, status: str) -> tuple[str | None, str | None]:
        edge = next_edge(graph, source, status, edge_uses)
        if edge:
            eid = str(edge.get("id") or "")
            edge_uses[eid] = edge_uses.get(eid, 0) + 1
            return str(edge["target"]), None
        blocked = circuit_open_edge(graph, source, status, edge_uses)
        if blocked:
            cap = edge_limit(blocked)
            return None, f"Circuit open: edge {blocked.get('id')} limit {cap}"
        return None, None

    while current and steps < MAX_STEPS:
        steps += 1
        display = agent_display_name(current)
        yield _sse(
            {
                "event": "step",
                "agent_id": current,
                "status": "running",
                "message": f"Running {display}…",
            }
        )
        try:
            status, message = _run_agent(current, ctx)
        except Exception as exc:
            yield _sse(
                {
                    "event": "step",
                    "agent_id": current,
                    "status": "failed",
                    "message": str(exc),
                }
            )
            yield _sse({"event": "error", "error": str(exc)})
            return

        yield _sse(
            {
                "event": "step",
                "agent_id": current,
                "status": "done" if status not in ("failed", "fail") else "failed",
                "message": message,
                "result": status,
            }
        )
        if status in ("failed", "fail"):
            nxt, circuit_msg = pick_next(current, status)
            if circuit_msg:
                yield _sse(
                    {
                        "event": "step",
                        "agent_id": current,
                        "status": "failed",
                        "message": circuit_msg,
                    }
                )
                yield _sse({"event": "error", "error": circuit_msg})
                return
            if not nxt:
                yield _sse({"event": "error", "error": message})
                return
            current = nxt
            continue

        nxt, circuit_msg = pick_next(current, status)
        if circuit_msg:
            yield _sse(
                {
                    "event": "step",
                    "agent_id": current,
                    "status": "failed",
                    "message": circuit_msg,
                }
            )
            yield _sse({"event": "error", "error": circuit_msg})
            return
        current = nxt

    try:
        result = _package_result(ctx)
    except Exception as exc:
        yield _sse({"event": "error", "error": str(exc)})
        return
    yield _sse({"event": "result", **result})


def run_pipeline_sync(
    prompt: str,
    mode: str,
    *,
    language: str = "en",
    report_type: str | None = None,
    chart_type: str | None = None,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] | None = None
    error: str | None = None
    for chunk in pipeline_events(
        prompt,
        mode,
        language=language,
        report_type=report_type,
        chart_type=chart_type,
        columns=columns,
    ):
        line = chunk.strip()
        if not line.startswith("data:"):
            continue
        payload = json.loads(line[5:].strip())
        if payload.get("event") == "result":
            result = {k: v for k, v in payload.items() if k != "event"}
        if payload.get("event") == "error":
            error = str(payload.get("error") or "Run failed")
    if error:
        raise ValueError(error)
    if not result:
        raise ValueError("Pipeline produced no result")
    return result
