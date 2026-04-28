from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="mira-edu-assistant")
    messages: list[ChatMessage]
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    max_completion_tokens: int | None = Field(default=None, ge=1, le=4096)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, value: list[ChatMessage]) -> list[ChatMessage]:
        if not value:
            raise ValueError("messages must contain at least one item")
        return value

    @model_validator(mode="after")
    def token_limit_present(self) -> "ChatCompletionRequest":
        if self.max_tokens is None and self.max_completion_tokens is None:
            raise ValueError("max_tokens or max_completion_tokens is required")
        return self

    def requested_tokens(self) -> int:
        if self.max_completion_tokens is not None:
            return self.max_completion_tokens
        if self.max_tokens is not None:
            return self.max_tokens
        return 256


class CompletionRequest(BaseModel):
    model: str = Field(default="mira-edu-assistant")
    prompt: str = Field(min_length=1)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    max_completion_tokens: int | None = Field(default=None, ge=1, le=4096)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    @model_validator(mode="after")
    def token_limit_present(self) -> "CompletionRequest":
        if self.max_tokens is None and self.max_completion_tokens is None:
            raise ValueError("max_tokens or max_completion_tokens is required")
        return self

    def requested_tokens(self) -> int:
        if self.max_completion_tokens is not None:
            return self.max_completion_tokens
        if self.max_tokens is not None:
            return self.max_tokens
        return 256
