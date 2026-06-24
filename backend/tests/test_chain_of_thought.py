"""Tests for the chain-of-thought benchmark."""

from __future__ import annotations

import pytest

from apfel_bench.benchmarks.chain_of_thought import (
    _extract_final_number,
    ChainOfThoughtBenchmark,
)
from apfel_bench.client import ChatResponse


def test_extract_final_number_handles_answer_prefix():
    assert _extract_final_number("Step 1: 3+4=7\nStep 2: 7*2=14\nAnswer: 14") == 14.0


def test_extract_final_number_handles_equals_prefix():
    assert _extract_final_number("After working it out, 42 is the result. So = 42") == 42.0


def test_extract_final_number_handles_trailing_number():
    assert _extract_final_number("Working through it... I get 17.3") == 17.3


def test_extract_final_number_returns_none_when_no_number():
    assert _extract_final_number("I don't know how to solve this") is None


def test_extract_final_number_handles_negative():
    assert _extract_final_number("Answer: -5") == -5.0


def test_extract_final_number_handles_phrase_with_colon():
    # Should not be confused by numbers in the middle of the text
    assert _extract_final_number("The 3 cats and 2 dogs give us 5 animals in total.") == 5.0


def test_benchmark_answers_are_well_formed():
    bench = ChainOfThoughtBenchmark()
    for item in bench.PROBLEMS:
        assert isinstance(item["answer"], (int, float))
        assert item["q"].strip()


@pytest.mark.asyncio
async def test_benchmark_scores_when_answers_match():
    class FakeClient:
        def __init__(self, replies):
            self.idx = 0
            self.replies = replies

        async def chat(self, request):
            content = self.replies[self.idx]
            self.idx += 1
            return ChatResponse(
                content=content, prompt_tokens=10, completion_tokens=5, total_tokens=15, finish_reason="stop", raw={}
            )

    bench = ChainOfThoughtBenchmark()
    replies = [f"Thinking...\nAnswer: {item['answer']}" for item in bench.PROBLEMS]
    client = FakeClient(replies)
    result = await bench.run(client)
    assert result.benchmark == "chain_of_thought"
    assert result.score == 1.0
    assert result.metadata["correct"] == len(bench.PROBLEMS)
