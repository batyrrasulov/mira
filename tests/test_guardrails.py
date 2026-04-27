from __future__ import annotations

from mira.guardrails import GuardrailConfig, validate_payload


def test_guardrails_reject_missing_tokens() -> None:
    ok, errors = validate_payload(
        payload={"messages": [{"role": "user", "content": "hello"}]},
        endpoint="chat",
        config=GuardrailConfig(),
    )
    assert not ok
    assert any("max_tokens" in err for err in errors)


def test_guardrails_accept_valid_chat_payload() -> None:
    ok, errors = validate_payload(
        payload={
            "model": "mira-edu-assistant",
            "messages": [{"role": "user", "content": "Explain linear regression."}],
            "max_tokens": 64,
        },
        endpoint="chat",
        config=GuardrailConfig(max_input_chars=16000, max_output_tokens=512, min_output_tokens=1),
    )
    assert ok
    assert errors == []


def test_guardrails_accept_max_completion_tokens() -> None:
    ok, errors = validate_payload(
        payload={
            "model": "mira-edu-assistant",
            "messages": [{"role": "user", "content": "Explain linear regression."}],
            "max_completion_tokens": 64,
        },
        endpoint="chat",
        config=GuardrailConfig(max_input_chars=16000, max_output_tokens=512, min_output_tokens=1),
    )
    assert ok
    assert errors == []
