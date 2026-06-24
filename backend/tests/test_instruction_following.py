"""Instruction-following benchmark: enforces length / format constraints on the reply."""

from __future__ import annotations

import pytest

from apfel_bench.benchmarks.instruction_following import InstructionFollowingBenchmark
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


async def test_instruction_following_scores_one_when_response_within_word_limit():
    client = FakeApfelClient(content="The quick brown fox jumps.")  # 5 words
    bench = InstructionFollowingBenchmark(prompt="Describe a fox in exactly 5 words.", max_words=5)

    result = await bench.run(client)

    assert result.score == 1.0
    assert result.metadata["word_count"] == 5


async def test_instruction_following_scores_zero_when_response_exceeds_word_limit():
    client = FakeApfelClient(content="The quick brown fox jumps over the lazy dog tonight.")  # 10 words
    bench = InstructionFollowingBenchmark(prompt="Describe a fox in exactly 5 words.", max_words=5)

    result = await bench.run(client)

    assert result.score == 0.0
    assert result.metadata["word_count"] == 10


async def test_instruction_following_handles_zero_word_limit():
    client = FakeApfelClient(content="")
    bench = InstructionFollowingBenchmark(prompt="Reply with nothing.", max_words=0)

    result = await bench.run(client)

    assert result.score == 1.0
    assert result.metadata["word_count"] == 0


async def test_instruction_following_counts_words_by_whitespace():
    client = FakeApfelClient(content="  one   two\nthree\tfour  ")
    bench = InstructionFollowingBenchmark(prompt="x", max_words=10)

    result = await bench.run(client)

    assert result.metadata["word_count"] == 4
