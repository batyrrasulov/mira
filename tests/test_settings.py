from __future__ import annotations

from pathlib import Path

from mira.settings import load_settings


_ENV_KEYS = [
    "MIRA_HOST",
    "MIRA_PORT",
    "MIRA_REQUEST_TIMEOUT_S",
    "MIRA_API_KEY",
    "MIRA_MAX_INPUT_CHARS",
    "MIRA_MAX_OUTPUT_TOKENS",
    "MIRA_MIN_OUTPUT_TOKENS",
    "MIRA_LLM_BASE_URL",
    "MIRA_LLM_API_KEY",
    "MIRA_LLM_MODEL",
    "MIRA_UPSTREAM_CHAT_ENDPOINT",
    "MIRA_PROVIDER_TEMPERATURE",
    "MIRA_FORCE_FALLBACK",
    "MIRA_STRICT_JSON_MODE",
]


def _clear_mira_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_load_settings_prefers_app_env_over_stack_env(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configs = tmp_path / "configs"
    configs.mkdir(parents=True, exist_ok=True)
    (configs / "stack.env").write_text("MIRA_HOST=0.0.0.0\nMIRA_PORT=8080\n", encoding="utf-8")
    (configs / "app.env").write_text("MIRA_HOST=127.0.0.1\nMIRA_PORT=9090\n", encoding="utf-8")

    _clear_mira_env(monkeypatch)
    monkeypatch.chdir(tmp_path)

    settings = load_settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 9090


def test_load_settings_env_vars_override_files(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    configs = tmp_path / "configs"
    configs.mkdir(parents=True, exist_ok=True)
    (configs / "stack.env").write_text("MIRA_PORT=8080\n", encoding="utf-8")
    (configs / "app.env").write_text("MIRA_PORT=9090\n", encoding="utf-8")

    _clear_mira_env(monkeypatch)
    monkeypatch.setenv("MIRA_PORT", "7777")
    monkeypatch.chdir(tmp_path)

    settings = load_settings()
    assert settings.port == 7777
