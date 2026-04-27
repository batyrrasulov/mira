from __future__ import annotations

import json
from dataclasses import replace

from mira.contract import extract_json_object
from mira.llm_client import generate_learning_payload
from mira.settings import Settings


def _settings() -> Settings:
    return Settings(
        host="127.0.0.1",
        port=8080,
        request_timeout_s=5.0,
        api_key="",
        max_input_chars=16000,
        max_output_tokens=512,
        min_output_tokens=1,
        llm_base_url="",
        llm_api_key="",
        llm_model="",
        upstream_chat_endpoint="/v1/chat/completions",
        provider_temperature=0.1,
        force_fallback=False,
        strict_json_mode=True,
    )


def test_extract_json_object_from_embedded_text() -> None:
    parsed = extract_json_object("result:\n{\"learning_goal\": \"x\"}\nthanks")
    assert isinstance(parsed, dict)
    assert parsed["learning_goal"] == "x"


def test_generate_learning_payload_falls_back_when_unconfigured() -> None:
    result = generate_learning_payload(
        prompt="Explain gradient descent.",
        requested_tokens=120,
        settings=_settings(),
    )
    assert result.source == "fallback"
    assert "learning_goal" in result.payload


def test_generate_learning_payload_uses_provider_when_available(monkeypatch) -> None:
    class DummyResponse:
        status = 200

        def __enter__(self) -> "DummyResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def read(self) -> bytes:
            body = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "learning_goal": "Learn derivatives",
                                    "explanation": "Derivatives measure rate of change.",
                                    "guided_steps": [
                                        "Identify the function.",
                                        "Apply differentiation rules.",
                                        "Simplify the result.",
                                    ],
                                    "check_for_understanding": [
                                        "What does the derivative represent?",
                                        "How can you verify your result?",
                                    ],
                                    "policy_note": "Use this as study support.",
                                }
                            )
                        }
                    }
                ]
            }
            return json.dumps(body).encode("utf-8")

    def fake_urlopen(req, timeout):  # type: ignore[no-untyped-def]
        return DummyResponse()

    monkeypatch.setattr("mira.llm_client.urllib.request.urlopen", fake_urlopen)

    configured = replace(
        _settings(),
        llm_base_url="http://127.0.0.1:9000",
        llm_model="demo-model",
    )
    result = generate_learning_payload(
        prompt="Explain derivatives.",
        requested_tokens=180,
        settings=configured,
    )

    assert result.source == "provider"
    assert result.payload["learning_goal"] == "Learn derivatives"
