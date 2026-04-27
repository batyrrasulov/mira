from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import Body, FastAPI, HTTPException

from mira.guardrails import GuardrailConfig, validate_payload
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


def _heuristic_learning_payload(prompt: str) -> dict[str, Any]:
    compact = " ".join(prompt.split())
    focus = compact[:200] if compact else "the course topic"
    return {
        "learning_goal": f"Build understanding of: {focus}",
        "explanation": (
            "Start with the core concept in plain language, then connect it to one concrete class example. "
            "Focus on understanding, not answer-only output."
        ),
        "guided_steps": [
            "Restate the prompt in your own words.",
            "Identify required concepts and formulas.",
            "Solve one small example end-to-end.",
            "Explain why the result makes sense.",
        ],
        "check_for_understanding": [
            "What changed from your first interpretation?",
            "Which assumption is most important in your approach?",
            "How would you verify this result independently?",
        ],
        "policy_note": "This assistant is designed for learning support and concept mastery.",
    }


def _as_chat_completion(model: str, content: str, prompt_chars: int) -> dict[str, Any]:
    completion_tokens = max(1, len(content) // 4)
    prompt_tokens = max(1, prompt_chars // 4)
    return {
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
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "mira_api",
        "strict_json_mode": SETTINGS.strict_json_mode,
        "guardrails": {
            "max_input_chars": SETTINGS.max_input_chars,
            "max_output_tokens": SETTINGS.max_output_tokens,
            "min_output_tokens": SETTINGS.min_output_tokens,
        },
    }


@app.post("/v1/chat/completions")
def chat_completions(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    valid, errors = validate_payload(payload, endpoint="chat", config=GUARDRAILS)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    try:
        request = ChatCompletionRequest.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"errors": [str(exc)]}) from exc

    user_prompt = _latest_user_message([msg.model_dump() for msg in request.messages])
    learning_payload = _heuristic_learning_payload(user_prompt)
    if SETTINGS.strict_json_mode:
        content = json.dumps(learning_payload, ensure_ascii=True)
    else:
        content = learning_payload["explanation"]

    return _as_chat_completion(request.model, content, len(user_prompt))


@app.post("/v1/completions")
def completions(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    valid, errors = validate_payload(payload, endpoint="completion", config=GUARDRAILS)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    try:
        request = CompletionRequest.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"errors": [str(exc)]}) from exc

    learning_payload = _heuristic_learning_payload(request.prompt)
    text = json.dumps(learning_payload, ensure_ascii=True)
    completion = _as_chat_completion(request.model, text, len(request.prompt))
    completion["object"] = "text_completion"
    completion["choices"] = [
        {
            "index": 0,
            "text": text,
            "finish_reason": "stop",
        }
    ]
    return completion
