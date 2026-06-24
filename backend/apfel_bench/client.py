"""Thin async client for apfel's OpenAI-compatible chat completions API.

Only the surface we actually use is typed. Anything we add later grows
behind the same ChatRequest/ChatResponse shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


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


class HttpApfelClient:
    """httpx-backed ApfelClient that talks to a real apfel server."""

    def __init__(self, base_url: str, token: str | None = None, timeout: float = 60.0):
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=timeout
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        body: dict = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        if request.stream:
            body["stream"] = True
        for k, v in request.metadata.items():
            body[k] = v

        resp = await self._client.post("/chat/completions", json=body)
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})
        return ChatResponse(
            content=choice["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            raw=data,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
