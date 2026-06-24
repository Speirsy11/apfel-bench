"""Smoke benchmark: a tiny spec to prove the system end-to-end.

The benchmark asks apfel for "pong" and scores 1.0 if the expected token
appears (case-insensitive) in the response, else 0.0. It exists primarily
to prove the path from benchmark -> apfel client -> result works.
"""

import pytest

from apfel_bench.benchmarks.smoke import SmokeBenchmark
from apfel_bench.client import ChatRequest, ChatResponse


class FakeApfelClient:
    """In-memory ApfelClient for unit tests. No network, no apfel server."""

    def __init__(self, content: str = "pong", prompt_tokens: int = 2, completion_tokens: int = 5):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.last_request: ChatRequest | None = None

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.last_request = request
        return ChatResponse(
            content=self.content,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.prompt_tokens + self.completion_tokens,
            finish_reason="stop",
            raw={},
        )


async def test_smoke_benchmark_scores_one_when_response_contains_pong():
    """The benchmark should score 1.0 when the response contains 'pong'."""
    client = FakeApfelClient(content="Pong! 🏓")
    bench = SmokeBenchmark()

    result = await bench.run(client)

    assert result.score == 1.0
    assert result.benchmark == "smoke"
    assert "pong" in result.response.lower()


async def test_smoke_benchmark_scores_zero_when_response_lacks_pong():
    """The benchmark should score 0.0 when the response does not contain 'pong'."""
    client = FakeApfelClient(content="I will not comply with that request.")
    bench = SmokeBenchmark()

    result = await bench.run(client)

    assert result.score == 0.0
    assert result.benchmark == "smoke"


async def test_smoke_benchmark_records_token_counts():
    """The result should record prompt and completion tokens from the client response."""
    client = FakeApfelClient(content="pong", prompt_tokens=7, completion_tokens=3)
    bench = SmokeBenchmark()

    result = await bench.run(client)

    assert result.prompt_tokens == 7
    assert result.completion_tokens == 3


async def test_smoke_benchmark_sends_a_single_user_message():
    """The benchmark should send exactly one user message to the client."""
    client = FakeApfelClient()
    bench = SmokeBenchmark()

    await bench.run(client)

    assert client.last_request is not None
    assert len(client.last_request.messages) == 1
    assert client.last_request.messages[0].role == "user"
    assert "pong" in client.last_request.messages[0].content.lower()
