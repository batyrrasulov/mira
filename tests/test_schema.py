from __future__ import annotations

from mira.schema import ChatCompletionRequest, CompletionRequest


def test_chat_schema_accepts_large_message_payload() -> None:
    payload = {
        "model": "mira-edu-assistant",
        "messages": [{"role": "user", "content": "a" * 20000}],
        "max_tokens": 32,
    }
    request = ChatCompletionRequest.model_validate(payload)
    assert len(request.messages[0].content) == 20000


def test_completion_schema_accepts_large_prompt_payload() -> None:
    payload = {
        "model": "mira-edu-assistant",
        "prompt": "b" * 20000,
        "max_tokens": 32,
    }
    request = CompletionRequest.model_validate(payload)
    assert len(request.prompt) == 20000
