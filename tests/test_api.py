from __future__ import annotations

from dataclasses import replace
import json

from fastapi.testclient import TestClient

import mira.api as api_module

from mira.api import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "mira_api"


def test_chat_completions_contract() -> None:
    payload = {
        "model": "mira-edu-assistant",
        "messages": [{"role": "user", "content": "Help me understand binary search."}],
        "max_tokens": 120,
        "temperature": 0.0,
    }
    resp = client.post("/v1/chat/completions", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["object"] == "chat.completion"
    assert body["system_fingerprint"].startswith("mira:")
    assert "x_mira" in body
    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    assert "learning_goal" in parsed
    assert "guided_steps" in parsed


def test_auth_required_when_api_key_set() -> None:
    original = api_module.SETTINGS
    api_module.SETTINGS = replace(original, api_key="secret-token")
    try:
        payload = {
            "model": "mira-edu-assistant",
            "messages": [{"role": "user", "content": "Explain recursion."}],
            "max_tokens": 120,
            "temperature": 0.0,
        }

        unauthorized = client.post("/v1/chat/completions", json=payload)
        assert unauthorized.status_code == 401

        wrong_key = client.post(
            "/v1/chat/completions",
            json=payload,
            headers={"Authorization": "Bearer wrong"},
        )
        assert wrong_key.status_code == 401

        authorized = client.post(
            "/v1/chat/completions",
            json=payload,
            headers={"Authorization": "Bearer secret-token"},
        )
        assert authorized.status_code == 200
    finally:
        api_module.SETTINGS = original
