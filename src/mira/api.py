from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, status

from mira.guardrails import GuardrailConfig, validate_payload
from mira.llm_client import generate_learning_payload, probe_upstream
from mira.schema import ChatCompletionRequest, CompletionRequest
from mira.settings import load_settings

SETTINGS = load_settings()
GUARDRAILS = GuardrailConfig(
    max_input_chars=SETTINGS.max_input_chars,
    max_output_tokens=SETTINGS.max_output_tokens,
    min_output_tokens=SETTINGS.min_output_tokens,
)

app = FastAPI(title="Mira API", version="0.1.0")


def _latest_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")
            if isinstance(content, str):
                return content.strip()
    return ""


def _resolve_requested_tokens(payload: dict[str, Any], default_tokens: int) -> int:
    for key in ("max_completion_tokens", "max_tokens"):
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value > 0:
            return value
    return max(1, default_tokens)


def _as_chat_completion(
    model: str,
    content: str,
    prompt_chars: int,
    source: str,
    generation_error: str,
) -> dict[str, Any]:
    completion_tokens = max(1, len(content) // 4)
    prompt_tokens = max(1, prompt_chars // 4)
    response = {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "system_fingerprint": f"mira:{source}",
        "x_mira": {
            "source": source,
            "fallback_used": source != "provider",
        },
    }
    if generation_error:
        response["x_mira"]["warning"] = generation_error
    return response


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix, _, token = authorization.partition(" ")
    if prefix.lower() != "bearer":
        return ""
    return token.strip()


def _authorize_request(authorization: str | None) -> None:
    if not SETTINGS.api_key:
        return

    token = _extract_bearer_token(authorization)
    if token != SETTINGS.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"errors": ["unauthorized"]},
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "mira_api",
        "auth_required": bool(SETTINGS.api_key),
        "strict_json_mode": SETTINGS.strict_json_mode,
        "provider": {
            "configured": bool(SETTINGS.llm_base_url and SETTINGS.llm_model),
            "base_url": SETTINGS.llm_base_url,
            "model": SETTINGS.llm_model,
            "force_fallback": SETTINGS.force_fallback,
        },
        "guardrails": {
            "max_input_chars": SETTINGS.max_input_chars,
            "max_output_tokens": SETTINGS.max_output_tokens,
            "min_output_tokens": SETTINGS.min_output_tokens,
        },
    }


@app.get("/ready")
def ready() -> dict[str, Any]:
    probe = probe_upstream(SETTINGS)
    if not probe.ok:
        raise HTTPException(status_code=503, detail={"status": "degraded", "reason": probe.detail})
    return {"status": "ok", "reason": probe.detail}


@app.post("/v1/chat/completions")
def chat_completions(
    payload: dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _authorize_request(authorization)

    valid, errors = validate_payload(payload, endpoint="chat", config=GUARDRAILS)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    try:
        request = ChatCompletionRequest.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"errors": [str(exc)]}) from exc

    user_prompt = _latest_user_message([msg.model_dump() for msg in request.messages])
    requested_tokens = _resolve_requested_tokens(payload, request.requested_tokens())
    generation = generate_learning_payload(
        prompt=user_prompt,
        requested_tokens=requested_tokens,
        settings=SETTINGS,
    )

    if SETTINGS.strict_json_mode:
        content = json.dumps(generation.payload, ensure_ascii=True)
    else:
        content = generation.payload["explanation"]

    return _as_chat_completion(
        request.model,
        content,
        len(user_prompt),
        generation.source,
        generation.error,
    )


@app.post("/v1/completions")
def completions(
    payload: dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _authorize_request(authorization)

    valid, errors = validate_payload(payload, endpoint="completion", config=GUARDRAILS)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    try:
        request = CompletionRequest.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"errors": [str(exc)]}) from exc

    requested_tokens = _resolve_requested_tokens(payload, request.requested_tokens())
    generation = generate_learning_payload(
        prompt=request.prompt,
        requested_tokens=requested_tokens,
        settings=SETTINGS,
    )

    text = json.dumps(generation.payload, ensure_ascii=True)
    completion = _as_chat_completion(
        request.model,
        text,
        len(request.prompt),
        generation.source,
        generation.error,
    )
    completion["object"] = "text_completion"
    completion["choices"] = [
        {
            "index": 0,
            "text": text,
            "finish_reason": "stop",
        }
    ]
    return completion
