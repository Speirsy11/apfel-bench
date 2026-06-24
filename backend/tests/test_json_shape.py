"""JSON-shape benchmark: forces the model to reply with JSON and validates it."""

from __future__ import annotations

import pytest

from apfel_bench.benchmarks.json_shape import JsonShapeBenchmark
from apfel_bench.client import ChatRequest, ChatResponse


class FakeApfelClient:
    def __init__(self, content: str):
        self.content = content
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            content=self.content,
            prompt_tokens=2,
            completion_tokens=2,
            total_tokens=4,
            finish_reason="stop",
            raw={},
        )


async def test_json_shape_scores_one_when_response_is_valid_matching_json():
    client = FakeApfelClient(content='{"x": 3, "y": "hello"}')
    bench = JsonShapeBenchmark()

    result = await bench.run(client)

    assert result.score == 1.0
    assert result.metadata["parsed"] == {"x": 3, "y": "hello"}


async def test_json_shape_extracts_json_from_code_fence():
    client = FakeApfelClient(content='Sure!\n```json\n{"x": 1, "y": "ok"}\n```')
    bench = JsonShapeBenchmark()

    result = await bench.run(client)

    assert result.score == 1.0
    assert result.metadata["parsed"] == {"x": 1, "y": "ok"}


async def test_json_shape_scores_zero_on_invalid_json():
    client = FakeApfelClient(content="not json at all")
    bench = JsonShapeBenchmark()

    result = await bench.run(client)

    assert result.score == 0.0
    assert "error" in result.metadata


async def test_json_shape_scores_zero_on_type_mismatch():
    client = FakeApfelClient(content='{"x": "not-an-int", "y": "ok"}')
    bench = JsonShapeBenchmark()

    result = await bench.run(client)

    assert result.score == 0.0
    assert "x" in result.metadata.get("error", "")


async def test_json_shape_uses_response_format_json():
    client = FakeApfelClient(content='{"x": 1, "y": "ok"}')
    bench = JsonShapeBenchmark()

    await bench.run(client)

    sent = client.requests[0]
    assert sent.metadata.get("response_format") == {"type": "json_object"}


async def test_json_shape_supports_custom_prompt_and_schema():
    bench = JsonShapeBenchmark(
        prompt="Return a person with name and age.",
        schema={"name": str, "age": int},
    )
    assert "name" in bench.prompt
    assert bench.schema["age"] is int
