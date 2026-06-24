"""Thin async client for apfel's OpenAI-compatible chat completions API.

Only the surface we actually use is typed. Anything we add later grows
behind the same ChatRequest/ChatResponse shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str
    raw: dict[str, Any] = field(default_factory=dict)


class ApfelClient(Protocol):
    """Anything that can send a ChatRequest and return a ChatResponse."""

    async def chat(self, request: ChatRequest) -> ChatResponse: ...

    async def aclose(self) -> None: ...
