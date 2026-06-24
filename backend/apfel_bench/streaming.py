"""Reusable streaming primitives for OpenAI-compatible chat APIs.

Two pure async-iterator transforms, intentionally split:

  * `sse_decode_bytes`    bytes stream         -> data payloads (text)
  * `openai_chat_chunks`  data payload stream  -> typed ChatChunk stream

Why split? SSE framing is a transport concern (it applies to anything
emitting text/event-stream). The OpenAI chunk shape is a protocol concern
(it applies to anything that speaks `/v1/chat/completions` streaming,
including Ollama, vLLM, llama.cpp, Apfel, OpenAI itself, ...).

They compose trivially: `openai_chat_chunks(sse_decode_bytes(byte_stream))`.
Either transform can be reused on its own — feed a WebSocket into
`openai_chat_chunks`, or feed a different protocol's bytes into
`sse_decode_bytes`.

Pattern inspired by the opencode LLM provider's
`Framing.sse` / `Protocol.openai_chat` split
(<https://github.com/anomalyco/opencode>, `packages/llm/src`).

Cancellation: this is plain async iteration. Cancelling the consumer
cancels the producer at the next `await`, which closes the underlying
httpx response stream cleanly. No extra plumbing needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class ChatChunk:
    """One OpenAI chat-completion streaming chunk."""

    content_delta: str
    finish_reason: str | None
    raw: dict[str, Any] = field(default_factory=dict)


async def sse_decode_bytes(byte_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
    """Decode a Server-Sent Events byte stream into the JSON `data:` payloads.

    Skips:
      * empty `data:` lines
      * the `data: [DONE]` sentinel
      * non-data SSE fields (`event:`, `id:`, `retry:`) and comment lines
      * blank separator lines between events

    Handles events split arbitrarily across byte chunks (the byte stream
    boundary is independent of the SSE event boundary).
    """
    buffer = b""
    async for raw in byte_stream:
        buffer += raw
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line = line.rstrip(b"\r").decode("utf-8", errors="replace")
            if not line or not line.startswith("data:"):
                continue  # comment, event:, id:, retry:, blank
            payload = line[5:].lstrip()
            if not payload or payload == "[DONE]":
                continue
            yield payload


async def openai_chat_chunks(
    payload_stream: AsyncIterator[str],
) -> AsyncIterator[ChatChunk]:
    """Parse an OpenAI chat-completion streaming payload stream into typed chunks.

    Each input payload is a JSON object whose `choices[0].delta` carries the
    new content and optional `finish_reason`. This is the standard shape
    shared by Apfel, Ollama, OpenAI, vLLM, llama.cpp's server, and most
    OpenAI-compatible providers.
    """
    async for payload in payload_stream:
        data = json.loads(payload)
        choice = data["choices"][0]
        delta = choice.get("delta") or {}
        yield ChatChunk(
            content_delta=delta.get("content") or "",
            finish_reason=choice.get("finish_reason"),
            raw=data,
        )
