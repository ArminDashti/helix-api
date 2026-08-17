"""Walk the arranged pipeline and produce a real report payload."""

from __future__ import annotations

import json
import time as _agent_time
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


def _ui_text(language: str, en: str, fa: str) -> str:
    return fa if language == "fa" else en


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _agent_debug_log(location: str, message: str, data: dict[str, Any], hypothesis_id: str) -> None:
    # #region agent log
    try:
        with open(
            r"C:\Users\armin\GitHub\helix-api\debug-9f5f92.log",
            "a",
            encoding="utf-8",
        ) as _agent_log:
            _agent_log.write(
                json.dumps(
                    {
                        "sessionId": "9f5f92",
                        "timestamp": int(_agent_time.time() * 1000),
                        "location": location,
                        "message": message,
                        "data": data,
                        "hypothesisId": hypothesis_id,
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion


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
    language = ctx.get("language") or "en"
    if language == "fa":
        user += (
            "\nWrite text_report and the user-visible message in Persian (فارسی). "
            "Keep SQL, schema.table names, and catalog identifiers unchanged."
        )
    else:
        user += (
            "\nWrite text_report and the user-visible message in English. "
            "Keep SQL, schema.table names, and catalog identifiers unchanged."
        )
    if agent_id == "sql":
        user += (
            "\nAlso include a sql field with one SELECT for the Pakhsh warehouse. "
            "Use schema.table names from the warehouse catalog "
            "(for order lines use Sales.DarkhastFaktorSatr, not SalesLT.SalesOrderDetail). "
            "Do not use AdventureWorks or SalesLT objects; they are not in this warehouse. "
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
        # #region agent log
        _sql_started = _agent_time.time()
        _agent_debug_log(
            "pipeline_run.py:_run_agent",
            "SQL execute start",
            {"agent_id": agent_id, "sql_len": len(sql_text)},
            "D",
        )
        try:
            with open(
                r"C:\Users\armin\GitHub\helix-webui\debug-604d40.log",
                "a",
                encoding="utf-8",
            ) as _dbg604:
                _dbg604.write(
                    json.dumps(
                        {
                            "sessionId": "604d40",
                            "timestamp": int(_agent_time.time() * 1000),
                            "location": "pipeline_run.py:_run_agent",
                            "message": "SQL agent output before execute",
                            "data": {
                                "sql_preview": sql_text[:800],
                                "system_has_saleslt_salesorderdetail": "SalesLT.SalesOrderDetail"
                                in system,
                                "system_has_darkhastfaktorsatr": "Sales.DarkhastFaktorSatr"
                                in system,
                                "sql_has_saleslt": "SalesLT" in sql_text,
                                "sql_has_pakhsh_sales": "Sales." in sql_text,
                            },
                            "hypothesisId": "A",
                            "runId": "post-fix",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        fetch = execute_select(sql_text)
        # #region agent log
        _agent_debug_log(
            "pipeline_run.py:_run_agent",
            "SQL execute done",
            {
                "agent_id": agent_id,
                "row_count": len(fetch.get("rows") or []),
                "elapsed_s": round(_agent_time.time() - _sql_started, 2),
            },
            "D",
        )
        # #endregion
        ctx["sql_fetch"] = fetch
        ctx.setdefault("artifacts", {})[agent_id] = {
            "sql": fetch["sql"],
            "row_count": len(fetch["rows"]),
            "message": message,
        }
        return "done", message or _ui_text(
            language,
            f"Fetched {len(fetch['rows'])} rows",
            f"{len(fetch['rows'])} ردیف دریافت شد",
        )

    artifacts = ctx.setdefault("artifacts", {})
    artifacts[agent_id] = {
        "message": message,
        "text": parsed.get("text_report") or parsed.get("text") or message,
    }
    if agent_id == "response_publisher" and parsed.get("text_report"):
        ctx["text_report"] = str(parsed.get("text_report"))
    if agent_id == "implementation_auditor":
        if result in ("pass", "done", "success"):
            return "pass", message or _ui_text(
                language, "Blueprint matched", "طرح تطبیق کرد"
            )
        return "fail", message or _ui_text(
            language, "Blueprint not matched", "طرح تطبیق نکرد"
        )
    if result in ("failed", "fail", "error", "failure"):
        return "failed", message
    return "done", message or _ui_text(
        language,
        f"{agent_display_name(agent_id)} complete",
        f"{agent_display_name(agent_id)} کامل شد",
    )


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
            "message": _ui_text(
                language,
                f"Received prompt ({mode}/{language}) via {provider}: {prompt[:120]}",
                f"درخواست دریافت شد ({mode}/{language}) از {provider}: {prompt[:120]}",
            ),
        }
    )

    entry = graph.get("entry")
    if not entry:
        raise ValueError("Pipeline has no entry agent")

    edge_uses: dict[str, int] = {}
    current: str | None = str(entry)
    steps = 0
    pipeline_started = _agent_time.time()
    _agent_debug_log(
        "pipeline_run.py:pipeline_events",
        "Pipeline start",
        {"mode": mode, "entry": entry},
        "B",
    )

    def pick_next(source: str, status: str) -> tuple[str | None, str | None]:
        edge = next_edge(graph, source, status, edge_uses)
        if edge:
            eid = str(edge.get("id") or "")
            edge_uses[eid] = edge_uses.get(eid, 0) + 1
            return str(edge["target"]), None
        blocked = circuit_open_edge(graph, source, status, edge_uses)
        if blocked:
            cap = edge_limit(blocked)
            return None, _ui_text(
                language,
                f"Circuit open: edge {blocked.get('id')} limit {cap}",
                f"مدار باز: یال {blocked.get('id')} حد {cap}",
            )
        return None, None

    while current and steps < MAX_STEPS:
        steps += 1
        display = agent_display_name(current)
        _agent_debug_log(
            "pipeline_run.py:pipeline_events",
            "Agent step start",
            {
                "step": steps,
                "agent_id": current,
                "elapsed_s": round(_agent_time.time() - pipeline_started, 2),
            },
            "E",
        )
        yield _sse(
            {
                "event": "step",
                "agent_id": current,
                "status": "running",
                "message": _ui_text(
                    language,
                    f"Running {display}…",
                    f"در حال اجرای {display}…",
                ),
            }
        )
        try:
            status, message = _run_agent(current, ctx)
        except Exception as exc:
            _agent_debug_log(
                "pipeline_run.py:pipeline_events",
                "Agent step failed",
                {
                    "step": steps,
                    "agent_id": current,
                    "error": str(exc),
                    "elapsed_s": round(_agent_time.time() - pipeline_started, 2),
                },
                "B",
            )
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
