from __future__ import annotations

import json

from fastapi.testclient import TestClient

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
    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    assert "learning_goal" in parsed
    assert "guided_steps" in parsed
