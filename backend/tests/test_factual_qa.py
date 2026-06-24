"""Tests for the Factual QA benchmark. TDD vertical slice."""

from __future__ import annotations

import pytest

from apfel_bench.benchmarks.factual_qa import _normalize_letter, FactualQABenchmark
from apfel_bench.client import ChatResponse


def test_normalize_letter_handles_bare_letter():
    assert _normalize_letter("B") == "B"


def test_normalize_letter_handles_explanation_then_letter():
    assert _normalize_letter("The capital is Sydney... no, wait, Canberra. C") == "C"


def test_normalize_letter_handles_answer_prefix():
    assert _normalize_letter("Answer: D") == "D"
    assert _normalize_letter("Answer is A.") == "A"


def test_normalize_letter_returns_none_for_garbage():
    assert _normalize_letter("I don't know") is None
    assert _normalize_letter("") is None


def test_benchmark_uses_unique_correct_answers_across_bank():
    # Sanity: ensure the bank is well-formed.
    bench = FactualQABenchmark()
    for item in bench.QUESTIONS:
        assert item["answer"] in {"A", "B", "C", "D"}
        assert len(item["options"]) == 4


@pytest.mark.asyncio
async def test_benchmark_scores_correct_and_records_per_question(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.calls: list[str] = []

        async def chat(self, request):
            self.calls.append(request.messages[0].content)
            # Always reply with A — predictable.
            return ChatResponse(
                content="A",
                prompt_tokens=10,
                completion_tokens=1,
                total_tokens=11,
                finish_reason="stop",
                raw={},
            )

    client = FakeClient()
    bench = FactualQABenchmark()
    result = await bench.run(client)

    expected_a = sum(1 for q in bench.QUESTIONS if q["answer"] == "A")
    assert result.benchmark == "factual_qa"
    assert result.score == expected_a / 10
    per_q = result.metadata["per_question"]
    assert len(per_q) == 10
    assert sum(1 for q in per_q if q["ok"]) == expected_a
    assert all("expected" in q and "got" in q for q in per_q)
