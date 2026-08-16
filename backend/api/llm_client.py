"""Chat completion client for the configured LLM provider."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from .config_loader import (
    cursor_cloud_json,
    get_agent_model,
    get_cursor_token,
    get_openrouter_token,
    get_provider,
)

_CURSOR_RUN_POLL_SEC = 2.0
_CURSOR_RUN_TIMEOUT_SEC = 300.0


def require_llm() -> tuple[str, str]:
    """Return (provider, token) or raise if the selected LLM cannot be used."""
    provider = get_provider()
    if provider == "cursor":
        token = get_cursor_token()
        if not token:
            raise ValueError("Cursor API key is not set")
        return "cursor", token
    token = get_openrouter_token()
    if not token:
        raise ValueError("OpenRouter API key is not set")
    return "openrouter", token


def complete_chat(agent_id: str, user_message: str, system_prompt: str) -> str:
    provider, token = require_llm()
    if provider == "cursor":
        return _complete_via_cursor_cloud(agent_id, user_message, system_prompt)
    return _complete_via_openrouter(agent_id, user_message, system_prompt, token)


def _complete_via_openrouter(
    agent_id: str, user_message: str, system_prompt: str, token: str
) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"

    model = get_agent_model(agent_id)
    if not model or model == "auto":
        model = "openai/gpt-4o-mini"

    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ValueError(f"LLM request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"LLM request failed: {exc.reason}") from exc

    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise ValueError("LLM returned no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    content = (message or {}).get("content") if isinstance(message, dict) else ""
    text = content if isinstance(content, str) else json.dumps(content)
    if not str(text).strip():
        raise ValueError("LLM returned an empty message")
    return str(text)


def _cursor_model_payload(agent_id: str) -> dict[str, Any] | None:
    model = get_agent_model(agent_id)
    if not model or model == "auto" or model.startswith("openai/"):
        return None
    return {"id": model}


def _cursor_run_result_text(payload: dict[str, Any]) -> str:
    raw = payload.get("result")
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return json.dumps(raw)
    return ""


def _complete_via_cursor_cloud(
    agent_id: str, user_message: str, system_prompt: str
) -> str:
    """Run a no-repo Cloud Agent and return its final assistant text."""
    prompt_text = (
        "You are a text-only assistant. Reply with the answer only. "
        "Do not edit files or use tools unless required to produce the answer.\n\n"
        f"System:\n{system_prompt}\n\nUser:\n{user_message}"
    )
    create_body: dict[str, Any] = {
        "prompt": {"text": prompt_text},
        "name": f"Helix {agent_id}"[:100],
    }
    model = _cursor_model_payload(agent_id)
    if model:
        create_body["model"] = model

    created = cursor_cloud_json("POST", "/v1/agents", create_body, timeout=180)
    if not isinstance(created, dict):
        raise ValueError("Cursor API returned an unexpected create payload")
    agent = created.get("agent") if isinstance(created.get("agent"), dict) else {}
    run = created.get("run") if isinstance(created.get("run"), dict) else {}
    agent_cloud_id = str(agent.get("id") or "").strip()
    run_id = str(run.get("id") or agent.get("latestRunId") or "").strip()
    if not agent_cloud_id or not run_id:
        raise ValueError("Cursor API did not return agent and run ids")

    try:
        deadline = time.monotonic() + _CURSOR_RUN_TIMEOUT_SEC
        status = str(run.get("status") or "")
        result_text = _cursor_run_result_text(run)
        first_poll = True
        while time.monotonic() < deadline:
            if status in {"ERROR", "CANCELLED", "EXPIRED"}:
                break
            if status == "FINISHED" and result_text:
                break
            if not first_poll:
                time.sleep(_CURSOR_RUN_POLL_SEC)
            first_poll = False
            polled = cursor_cloud_json(
                "GET",
                f"/v1/agents/{agent_cloud_id}/runs/{run_id}",
                timeout=30,
            )
            if not isinstance(polled, dict):
                raise ValueError("Cursor API returned an unexpected run payload")
            status = str(polled.get("status") or "")
            polled_text = _cursor_run_result_text(polled)
            if polled_text:
                result_text = polled_text
        else:
            raise ValueError("Cursor agent run timed out")

        if status != "FINISHED":
            raise ValueError(f"Cursor agent run ended with status {status}")
        if not result_text:
            raise ValueError("Cursor agent returned an empty message")
        return result_text
    finally:
        try:
            cursor_cloud_json("POST", f"/v1/agents/{agent_cloud_id}/archive", timeout=30)
        except ValueError:
            pass


def parse_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return {"text": text}
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {"text": text}
    return data if isinstance(data, dict) else {"text": text}
