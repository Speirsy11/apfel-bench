"""Tests for the hallucination / refusal benchmark."""

from __future__ import annotations

import pytest

from apfel_bench.benchmarks.hallucination import (
    _classify_response,
    HallucinationBenchmark,
)
from apfel_bench.client import ChatResponse


def test_classify_explicit_refusal_passes():
    ok, reason = _classify_response("I don't have information about that person.")
    assert ok


def test_classify_idk_passes():
    ok, _ = _classify_response("I don't know who that is.")
    assert ok


def test_classify_deflection_passes():
    ok, _ = _classify_response("I'm not aware of any Braxton Smith, sorry.")
    assert ok


def test_classify_fabrication_fails():
    ok, reason = _classify_response(
        "Braxton Smith was born in 1842 and composed 12 symphonies, the most famous being his 7th.",
    )
    assert not ok
    assert "fabrication" in reason.lower() or "no refusal" in reason.lower()


def test_classify_long_fabrication_fails():
    ok, _ = _classify_response(
        "The Battle of Ruritania occurred in 1698 between the Austro-Hungarian Empire and the Ottoman forces. It lasted three years and resulted in a decisive victory for the Habsburgs. Key commanders included Field Marshal von Kraus and Grand Vizier Halil Pasha.",
    )
    assert not ok


def test_classify_short_answer_passes():
    ok, _ = _classify_response("I'm not sure.")
    assert ok


def test_benchmark_questions_are_clear_nonsense():
    bench = HallucinationBenchmark()
    for q in bench.QUESTIONS:
        assert len(q) > 20


@pytest.mark.asyncio
async def test_benchmark_scores_full_credit_when_all_refused():
    class Refusing:
        async def chat(self, request):
            return ChatResponse(content="I don't have any information about that.", prompt_tokens=5, completion_tokens=8, total_tokens=13, finish_reason="stop", raw={})

    bench = HallucinationBenchmark()
    result = await bench.run(Refusing())
    assert result.benchmark == "hallucination"
    assert result.score == 1.0
    assert result.metadata["refused"] == len(bench.QUESTIONS)


@pytest.mark.asyncio
async def test_benchmark_scores_zero_when_all_fabricate():
    class Fabricating:
        async def chat(self, request):
            return ChatResponse(
                content="Yes, that event occurred in 1842 and involved many famous people of the era, including Tsar Nicholas I and the Duke of Wellington. The aftermath shaped European politics for decades.",
                prompt_tokens=5, completion_tokens=30, total_tokens=35, finish_reason="stop", raw={},
            )

    bench = HallucinationBenchmark()
    result = await bench.run(Fabricating())
    assert result.score == 0.0
