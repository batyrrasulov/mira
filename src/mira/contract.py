from __future__ import annotations

import json
from typing import Any

REQUIRED_KEYS = {
    "learning_goal",
    "explanation",
    "guided_steps",
    "check_for_understanding",
    "policy_note",
}


def fallback_learning_payload(prompt: str) -> dict[str, Any]:
    compact = " ".join(prompt.split())
    focus = compact[:220] if compact else "the requested topic"
    return {
        "learning_goal": f"Understand and apply: {focus}",
        "explanation": (
            "Break the topic into first principles, then apply one worked example and one validation check."
        ),
        "guided_steps": [
            "Reframe the question in your own words.",
            "List the concepts, formulas, or assumptions you need.",
            "Solve a concrete example step by step.",
            "Verify the result using a second method or sanity check.",
        ],
        "check_for_understanding": [
            "What assumption controls the final answer most strongly?",
            "What would change if one input changed by 10%?",
            "How would you explain your method to a classmate?",
        ],
        "policy_note": "Use this response for learning and concept mastery.",
    }


def extract_json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None

    return None


def _as_text(value: Any, fallback: str) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text:
            return text
    return fallback


def _as_text_list(value: Any, fallback: list[str], min_items: int) -> list[str]:
    items: list[str] = []

    if isinstance(value, str):
        split_items = [part.strip() for part in value.replace("\n", ";").split(";")]
        items = [item for item in split_items if item]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]

    if len(items) < min_items:
        return fallback
    return items


def normalize_learning_payload(payload: dict[str, Any], prompt: str) -> dict[str, Any]:
    fallback = fallback_learning_payload(prompt)
    normalized = {
        "learning_goal": _as_text(payload.get("learning_goal"), fallback["learning_goal"]),
        "explanation": _as_text(payload.get("explanation"), fallback["explanation"]),
        "guided_steps": _as_text_list(payload.get("guided_steps"), fallback["guided_steps"], min_items=3),
        "check_for_understanding": _as_text_list(
            payload.get("check_for_understanding"),
            fallback["check_for_understanding"],
            min_items=2,
        ),
        "policy_note": _as_text(payload.get("policy_note"), fallback["policy_note"]),
    }

    missing = REQUIRED_KEYS - set(normalized.keys())
    if missing:
        return fallback

    return normalized
