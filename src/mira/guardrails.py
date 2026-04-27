from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GuardrailConfig:
    max_input_chars: int = 16000
    max_output_tokens: int = 512
    min_output_tokens: int = 1


def _extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _requested_tokens(payload: dict[str, Any]) -> int:
    value = payload.get("max_tokens")
    if value is None:
        return 0
    if isinstance(value, bool):
        return -1
    if not isinstance(value, int):
        return -1
    return value


def _chat_input_chars(payload: dict[str, Any]) -> int:
    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        return -1
    total = 0
    for msg in messages:
        if not isinstance(msg, dict):
            return -1
        total += len(_extract_text(msg.get("content", "")))
    return total


def _completion_input_chars(payload: dict[str, Any]) -> int:
    prompt = payload.get("prompt", "")
    if isinstance(prompt, str):
        return len(prompt)
    if isinstance(prompt, list):
        return len("".join(item for item in prompt if isinstance(item, str)))
    return -1


def validate_payload(
    payload: dict[str, Any],
    endpoint: str,
    config: GuardrailConfig,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return False, ["payload must be a JSON object"]

    tokens = _requested_tokens(payload)
    if tokens < 0:
        errors.append("max_tokens must be an integer")
    elif tokens == 0:
        errors.append("max_tokens is required")
    else:
        if tokens < config.min_output_tokens:
            errors.append(
                f"requested output tokens ({tokens}) is below minimum ({config.min_output_tokens})"
            )
        if tokens > config.max_output_tokens:
            errors.append(
                f"requested output tokens ({tokens}) exceeds limit ({config.max_output_tokens})"
            )

    if endpoint == "chat":
        chars = _chat_input_chars(payload)
        if chars < 0:
            errors.append("messages must be a list of objects")
        elif chars > config.max_input_chars:
            errors.append(f"input chars ({chars}) exceeds limit ({config.max_input_chars})")
    elif endpoint == "completion":
        chars = _completion_input_chars(payload)
        if chars < 0:
            errors.append("prompt must be a string or list of strings")
        elif chars > config.max_input_chars:
            errors.append(f"input chars ({chars}) exceeds limit ({config.max_input_chars})")
    else:
        errors.append(f"unsupported endpoint: {endpoint}")

    return len(errors) == 0, errors
