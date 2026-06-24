"""Tests for HttpApfelClient.stream_chat — the composed HTTP + SSE + OpenAI path."""

from __future__ import annotations

import os
import subprocess

import httpx
import pytest
import respx

from apfel_bench.client import ChatMessage, ChatRequest, HttpApfelClient
from apfel_bench.streaming import ChatChunk


async def test_stream_chat_yields_typed_chunks_from_sse():
    with respx.mock(assert_all_mocked=False) as mock:
        mock.post("http://apfel.local:11435/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=(
                    b'data: {"choices":[{"index":0,"delta":{"role":"assistant"}}]}\n\n'
                    b'data: {"choices":[{"index":0,"delta":{"content":"Hel"}}]}\n\n'
                    b'data: {"choices":[{"index":0,"delta":{"content":"lo"}}]}\n\n'
                    b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
                    b'data: [DONE]\n\n'
                ),
            )
        )
        client = HttpApfelClient(base_url="http://apfel.local:11435/v1", token="secret")
        request = ChatRequest(
            model="apple-foundationmodel",
            messages=[ChatMessage(role="user", content="hi")],
            stream=True,
        )
        chunks: list[ChatChunk] = []
        async for c in client.stream_chat(request):
            chunks.append(c)
        await client.aclose()

    deltas = [c.content_delta for c in chunks]
    assert deltas == ["", "Hel", "lo", ""]  # first is role-only, last is finish
    assert chunks[-1].finish_reason == "stop"


async def test_stream_chat_sends_stream_true_and_bearer_auth():
    with respx.mock(assert_all_mocked=False) as mock:
        route = mock.post("http://apfel.local:11435/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=b'data: {"choices":[{"index":0,"delta":{"content":"x"}}]}\n\ndata: [DONE]\n\n',
            )
        )
        client = HttpApfelClient(base_url="http://apfel.local:11435/v1", token="secret")
        async for _ in client.stream_chat(
            ChatRequest(
                model="apple-foundationmodel",
                messages=[ChatMessage(role="user", content="hi")],
                stream=True,
            )
        ):
            pass
        await client.aclose()

        sent = route.calls.last.request
        assert sent.headers["authorization"] == "Bearer secret"
        body = sent.content.decode()
        assert '"stream":true' in body or '"stream": true' in body


async def test_stream_chat_raises_on_apfel_error_status():
    with respx.mock(assert_all_mocked=False) as mock:
        mock.post("http://apfel.local:11435/v1/chat/completions").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        client = HttpApfelClient(base_url="http://apfel.local:11435/v1", token="secret")
        with pytest.raises(httpx.HTTPStatusError):
            async for _ in client.stream_chat(
                ChatRequest(
                    model="apple-foundationmodel",
                    messages=[ChatMessage(role="user", content="hi")],
                    stream=True,
                )
            ):
                pass
        await client.aclose()


@pytest.mark.integration
async def test_stream_chat_against_real_apfel_streams_tokens():
    """Live test against the apfel server. Set APFEL_INTEGRATION=1 to run."""
    if not os.environ.get("APFEL_INTEGRATION"):
        pytest.skip("set APFEL_INTEGRATION=1 to run")
    token = subprocess.check_output(
        ["security", "find-generic-password", "-a", "value", "-s", "openclaw/apfel/token", "-w"],
        text=True,
    ).strip()
    client = HttpApfelClient(base_url="http://127.0.0.1:11435/v1", token=token)
    chunks: list[ChatChunk] = []
    async for c in client.stream_chat(
        ChatRequest(
            model="apple-foundationmodel",
            messages=[ChatMessage(role="user", content="Count: 1, 2, 3")],
            stream=True,
        )
    ):
        chunks.append(c)
    await client.aclose()

    full = "".join(c.content_delta for c in chunks)
    assert "1" in full and "3" in full
    # We should have seen at least 2 chunks (real streaming)
    assert len([c for c in chunks if c.content_delta]) >= 2
    assert chunks[-1].finish_reason == "stop"
