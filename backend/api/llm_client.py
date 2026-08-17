"""Chat completion client for the configured LLM provider."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

import socket

from .config_loader import (
    get_agent_model,
    get_llm_base_url,
    get_llm_timeout_seconds,
    get_openrouter_settings,
    get_openrouter_token,
    get_provider,
)

_OPENROUTER_AUTO_MODEL = "openai/gpt-4o-mini"
_OPENAI_COMPAT_AUTO_MODEL = "gpt-4o-mini"


def require_llm() -> tuple[str, str, str]:
    """Return (provider, token, base_url) or raise if the selected LLM cannot be used."""
    provider = get_provider()
    token = get_openrouter_token()
    if not token:
        raise ValueError("API key is not set")
    base_url = get_llm_base_url()
    if not base_url:
        raise ValueError("Base URL is not set")
    return provider, token, base_url


def complete_chat(agent_id: str, user_message: str, system_prompt: str) -> str:
    provider, token, base_url = require_llm()
    return _complete_via_chat_completions(
        agent_id, user_message, system_prompt, token, base_url, provider
    )


def _complete_via_chat_completions(
    agent_id: str,
    user_message: str,
    system_prompt: str,
    token: str,
    base_url: str,
    provider: str,
) -> str:
    url = f"{base_url}/chat/completions"

    model = get_agent_model(agent_id)
    if not model or model == "auto":
        model = (
            _OPENROUTER_AUTO_MODEL
            if provider == "openrouter"
            else _OPENAI_COMPAT_AUTO_MODEL
        )

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
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if provider == "openrouter":
        app_name = str(get_openrouter_settings().get("app_name") or "Helix")
        headers["HTTP-Referer"] = "https://helix.local"
        headers["X-Title"] = app_name
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers=headers,
    )
    timeout_s = get_llm_timeout_seconds()
    # #region agent log
    import time as _agent_time

    _llm_started = _agent_time.time()
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
                        "location": "llm_client.py:_complete_via_chat_completions",
                        "message": "LLM call start",
                        "data": {
                            "agent_id": agent_id,
                            "model": model,
                            "provider": provider,
                            "timeout_s": timeout_s,
                            "runId": "post-fix",
                        },
                        "hypothesisId": "A",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
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
                            "location": "llm_client.py:_complete_via_chat_completions",
                            "message": "LLM HTTP error",
                            "data": {
                                "agent_id": agent_id,
                                "code": exc.code,
                                "elapsed_s": round(_agent_time.time() - _llm_started, 2),
                                "detail": detail[:120],
                            },
                            "hypothesisId": "A",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        raise ValueError(f"LLM request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
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
                            "location": "llm_client.py:_complete_via_chat_completions",
                            "message": "LLM URL error",
                            "data": {
                                "agent_id": agent_id,
                                "reason": str(exc.reason),
                                "elapsed_s": round(_agent_time.time() - _llm_started, 2),
                            },
                            "hypothesisId": "A",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        raise ValueError(f"LLM request failed: {exc.reason}") from exc
    except TimeoutError as exc:
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
                            "location": "llm_client.py:_complete_via_chat_completions",
                            "message": "LLM timeout",
                            "data": {
                                "agent_id": agent_id,
                                "timeout_s": timeout_s,
                                "elapsed_s": round(_agent_time.time() - _llm_started, 2),
                            },
                            "hypothesisId": "A",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        raise ValueError(
            f"LLM request timed out after {timeout_s}s — increase openrouter.timeout_seconds in helix.config.yaml"
        ) from exc
    except socket.timeout as exc:
        raise ValueError(
            f"LLM request timed out after {timeout_s}s — increase openrouter.timeout_seconds in helix.config.yaml"
        ) from exc
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
                        "location": "llm_client.py:_complete_via_chat_completions",
                        "message": "LLM call ok",
                        "data": {
                            "agent_id": agent_id,
                            "elapsed_s": round(_agent_time.time() - _llm_started, 2),
                        },
                        "hypothesisId": "A",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise ValueError("LLM returned no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    content = (message or {}).get("content") if isinstance(message, dict) else ""
    text = content if isinstance(content, str) else json.dumps(content)
    if not str(text).strip():
        raise ValueError("LLM returned an empty message")
    return str(text)


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
