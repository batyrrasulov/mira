from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from mira.contract import extract_json_object, fallback_learning_payload, normalize_learning_payload
from mira.settings import Settings

SYSTEM_PROMPT = (
    "You are a learning assistant. Return strict JSON only with keys: "
    "learning_goal, explanation, guided_steps, check_for_understanding, policy_note. "
    "guided_steps and check_for_understanding must be arrays of short strings."
)


@dataclass(frozen=True)
class GenerationResult:
    payload: dict[str, Any]
    source: str
    error: str = ""
    raw_content: str = ""


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    detail: str


def _join_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"


def _extract_choice_content(choice: dict[str, Any]) -> str:
    message = choice.get("message")
    if isinstance(message, dict):
        content = message.get("content", "")
    else:
        content = choice.get("text", "")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text", "")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts)

    return ""


def _build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _call_upstream(prompt: str, requested_tokens: int, settings: Settings) -> tuple[bool, str, str]:
    url = _join_url(settings.llm_base_url, settings.upstream_chat_endpoint)
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max(1, min(requested_tokens, settings.max_output_tokens)),
        "temperature": max(0.0, min(1.0, settings.provider_temperature)),
    }

    if settings.strict_json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        headers=_build_headers(settings.llm_api_key),
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=settings.request_timeout_s) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, "", f"upstream HTTP {exc.code}: {detail[:220]}"
    except Exception as exc:  # noqa: BLE001
        return False, "", f"upstream unavailable: {type(exc).__name__}: {exc}"

    choices = body.get("choices", []) if isinstance(body, dict) else []
    if not isinstance(choices, list) or not choices:
        return False, "", "upstream response missing choices"

    first = choices[0] if isinstance(choices[0], dict) else {}
    content = _extract_choice_content(first)
    if not content:
        return False, "", "upstream response missing content"

    return True, content, ""


def generate_learning_payload(prompt: str, requested_tokens: int, settings: Settings) -> GenerationResult:
    fallback = fallback_learning_payload(prompt)

    if settings.force_fallback:
        return GenerationResult(payload=fallback, source="fallback", error="forced_fallback")

    if not settings.llm_base_url or not settings.llm_model:
        return GenerationResult(payload=fallback, source="fallback", error="upstream_not_configured")

    ok, raw_content, error = _call_upstream(prompt, requested_tokens, settings)
    if not ok:
        return GenerationResult(payload=fallback, source="fallback", error=error)

    parsed = extract_json_object(raw_content)
    if parsed is None:
        return GenerationResult(
            payload=fallback,
            source="fallback",
            error="provider_content_not_json",
            raw_content=raw_content,
        )

    normalized = normalize_learning_payload(parsed, prompt)
    return GenerationResult(payload=normalized, source="provider", raw_content=raw_content)


def probe_upstream(settings: Settings) -> ProbeResult:
    if settings.force_fallback:
        return ProbeResult(ok=True, detail="forced_fallback")

    if not settings.llm_base_url or not settings.llm_model:
        return ProbeResult(ok=True, detail="fallback_mode")

    url = _join_url(settings.llm_base_url, "/v1/models")
    req = urllib.request.Request(url, headers=_build_headers(settings.llm_api_key), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=settings.request_timeout_s) as resp:
            if int(resp.status) == 200:
                return ProbeResult(ok=True, detail="provider_reachable")
            return ProbeResult(ok=False, detail=f"provider_status_{int(resp.status)}")
    except urllib.error.HTTPError as exc:
        return ProbeResult(ok=False, detail=f"provider_http_{exc.code}")
    except Exception as exc:  # noqa: BLE001
        return ProbeResult(ok=False, detail=f"provider_unreachable_{type(exc).__name__}")
