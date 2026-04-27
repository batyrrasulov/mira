from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    request_timeout_s: float
    api_key: str
    max_input_chars: int
    max_output_tokens: int
    min_output_tokens: int
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    upstream_chat_endpoint: str
    provider_temperature: float
    force_fallback: bool
    strict_json_mode: bool


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError:
        return default


def load_settings() -> Settings:
    env_candidates = [Path("configs/stack.env"), Path("configs/app.env")]
    for env_path in env_candidates:
        if env_path.exists():
            load_dotenv(env_path, override=False)

    return Settings(
        host=os.getenv("MIRA_HOST", "0.0.0.0").strip() or "0.0.0.0",
        port=_env_int("MIRA_PORT", 8080),
        request_timeout_s=_env_float("MIRA_REQUEST_TIMEOUT_S", 20.0),
        api_key=os.getenv("MIRA_API_KEY", "").strip(),
        max_input_chars=_env_int("MIRA_MAX_INPUT_CHARS", 16000),
        max_output_tokens=_env_int("MIRA_MAX_OUTPUT_TOKENS", 512),
        min_output_tokens=_env_int("MIRA_MIN_OUTPUT_TOKENS", 1),
        llm_base_url=os.getenv("MIRA_LLM_BASE_URL", "").strip(),
        llm_api_key=os.getenv("MIRA_LLM_API_KEY", "").strip(),
        llm_model=os.getenv("MIRA_LLM_MODEL", "").strip(),
        upstream_chat_endpoint=os.getenv("MIRA_UPSTREAM_CHAT_ENDPOINT", "/v1/chat/completions").strip()
        or "/v1/chat/completions",
        provider_temperature=_env_float("MIRA_PROVIDER_TEMPERATURE", 0.1),
        force_fallback=_env_bool("MIRA_FORCE_FALLBACK", False),
        strict_json_mode=_env_bool("MIRA_STRICT_JSON_MODE", True),
    )
