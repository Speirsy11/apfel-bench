"""httpx-backed ApfelClient that talks to a real apfel server."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from apfel_bench.client import ChatMessage, ChatRequest, HttpApfelClient


@pytest.fixture
def client() -> HttpApfelClient:
    return HttpApfelClient(base_url="http://apfel.local:11435/v1", token="secret")


async def test_http_client_sends_bearer_auth_when_token_set(client):
    with respx.mock(base_url="http://apfel.local:11435") as mock:
        route = mock.post("/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )
        )
        await client.chat(ChatRequest(model="apple-foundationmodel", messages=[ChatMessage(role="user", content="hi")]))
        await client.aclose()
        sent = route.calls.last.request
        assert sent.headers["authorization"] == "Bearer secret"


async def test_http_client_parses_openai_chat_response(client):
    with respx.mock(base_url="http://apfel.local:11435") as mock:
        mock.post("/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "pong"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
                },
            )
        )
        resp = await client.chat(
            ChatRequest(model="apple-foundationmodel", messages=[ChatMessage(role="user", content="say pong")])
        )
        await client.aclose()
    assert resp.content == "pong"
    assert resp.prompt_tokens == 3
    assert resp.completion_tokens == 1
    assert resp.total_tokens == 4
    assert resp.finish_reason == "stop"


async def test_http_client_raises_on_apfel_error(client):
    with respx.mock(base_url="http://apfel.local:11435") as mock:
        mock.post("/v1/chat/completions").mock(
            return_value=httpx.Response(500, json={"error": {"message": "boom"}})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.chat(ChatRequest(model="apple-foundationmodel", messages=[]))
        await client.aclose()


async def test_http_client_works_without_token():
    client = HttpApfelClient(base_url="http://apfel.local:11435/v1")
    with respx.mock(base_url="http://apfel.local:11435") as mock:
        route = mock.post("/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "x"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1},
                },
            )
        )
        await client.chat(ChatRequest(model="apple-foundationmodel", messages=[ChatMessage(role="user", content="x")]))
        await client.aclose()
        sent = route.calls.last.request
        assert "authorization" not in sent.headers


@pytest.mark.integration
async def test_http_client_against_real_apfel_returns_a_chat_completion():
    """Hits the live apfel server (skipped unless APFEL_INTEGRATION=1)."""
    import os
    if not os.environ.get("APFEL_INTEGRATION"):
        pytest.skip("set APFEL_INTEGRATION=1 to run")
    import subprocess
    token = subprocess.check_output(
        ["security", "find-generic-password", "-a", "value", "-s", "openclaw/apfel/token", "-w"],
        text=True,
    ).strip()
    client = HttpApfelClient(base_url="http://127.0.0.1:11435/v1", token=token)
    resp = await client.chat(
        ChatRequest(
            model="apple-foundationmodel",
            messages=[ChatMessage(role="user", content="Reply with only the single word: pong")],
        )
    )
    await client.aclose()
    assert "pong" in resp.content.lower()
    assert resp.prompt_tokens > 0
    assert resp.completion_tokens > 0
