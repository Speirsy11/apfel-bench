"""Streaming abstractions: SSE framing and OpenAI chat-completion protocol.

These are intentionally split into two pure async-iterator transforms so they
can be reused independently for other providers (Anthropic, Gemini, anything
that speaks SSE + JSON). Compose them in the HTTP client.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import pytest

from apfel_bench.streaming import ChatChunk, openai_chat_chunks, sse_decode_bytes


# --- helpers ---


async def _bytes(*chunks: bytes | str) -> AsyncIterator[bytes]:
    for c in chunks:
        yield c.encode("utf-8") if isinstance(c, str) else c


async def _strings(*items: str) -> AsyncIterator[str]:
    for s in items:
        yield s


async def _collect(async_iter) -> list:
    return [x async for x in async_iter]


# --- sse_decode_bytes ---


async def test_sse_decode_skips_done_sentinel():
    out = await _collect(sse_decode_bytes(_bytes('data: {"x":1}\n\n', "data: [DONE]\n\n")))
    assert out == ['{"x":1}']


async def test_sse_decode_skips_empty_data_and_comments():
    out = await _collect(
        sse_decode_bytes(
            _bytes(
                ": keep-alive\n",
                "data:\n\n",
                "data: hello\n\n",
                ": another comment\n",
            )
        )
    )
    assert out == ["hello"]


async def test_sse_decode_handles_events_split_across_byte_chunks():
    # An event whose 'data:' line straddles two byte chunks must still be assembled.
    out = await _collect(
        sse_decode_bytes(
            _bytes(
                b"data: {\"x\"",  # first half
                b":1}\n\n",  # second half + terminator
            )
        )
    )
    assert out == ['{"x":1}']


async def test_sse_decode_handles_multiple_events_in_one_chunk():
    out = await _collect(
        sse_decode_bytes(_bytes("data: a\n\ndata: b\n\ndata: c\n\n"))
    )
    assert out == ["a", "b", "c"]


async def test_sse_decode_ignores_event_id_retry_lines():
    out = await _collect(
        sse_decode_bytes(
            _bytes(
                "event: message\n",
                "id: 42\n",
                "retry: 3000\n",
                "data: payload\n",
                "\n",
            )
        )
    )
    assert out == ["payload"]


async def test_sse_decode_handles_crlf_line_endings():
    out = await _collect(sse_decode_bytes(_bytes("data: hi\r\n\r\n")))
    assert out == ["hi"]


# --- openai_chat_chunks ---


async def test_openai_chat_chunks_yields_content_delta():
    payload = json.dumps(
        {
            "id": "x",
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Hello"}}],
        }
    )
    chunks = await _collect(openai_chat_chunks(_strings(payload)))
    assert len(chunks) == 1
    assert chunks[0].content_delta == "Hello"
    assert chunks[0].finish_reason is None


async def test_openai_chat_chunks_handles_finish_reason():
    payload = json.dumps(
        {
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    )
    chunks = await _collect(openai_chat_chunks(_strings(payload)))
    assert chunks[0].finish_reason == "stop"
    assert chunks[0].content_delta == ""


async def test_openai_chat_chunks_handles_empty_delta():
    payload = json.dumps({"choices": [{"index": 0, "delta": {}}]})
    chunks = await _collect(openai_chat_chunks(_strings(payload)))
    assert chunks[0].content_delta == ""


async def test_openai_chat_chunks_handles_role_only_first_chunk():
    payload = json.dumps({"choices": [{"index": 0, "delta": {"role": "assistant"}}]})
    chunks = await _collect(openai_chat_chunks(_strings(payload)))
    assert chunks[0].content_delta == ""  # role is not content


async def test_openai_chat_chunks_compose_with_sse_decode():
    # The whole point: pipe bytes straight through to typed chunks.
    sse_blob = (
        'data: {"choices":[{"index":0,"delta":{"content":"Hel"}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"lo"},"finish_reason":"stop"}]}\n\n'
        "data: [DONE]\n\n"
    )
    chunks = await _collect(openai_chat_chunks(sse_decode_bytes(_bytes(sse_blob))))
    assert [c.content_delta for c in chunks] == ["Hel", "lo"]
    assert chunks[-1].finish_reason == "stop"
