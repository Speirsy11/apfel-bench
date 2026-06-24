"""Latency benchmark: runs N short prompts and reports tokens/sec."""

from __future__ import annotations

import pytest

from apfel_bench.benchmarks.latency import LatencyBenchmark
from apfel_bench.client import ChatRequest, ChatResponse


class FakeApfelClient:
    def __init__(self, content: str = "hi", completion_tokens: int = 2, delay_ms: int = 0):
        self.content = content
        self.completion_tokens = completion_tokens
        self.delay_ms = delay_ms
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if self.delay_ms:
            import asyncio
            await asyncio.sleep(self.delay_ms / 1000)
        return ChatResponse(
            content=self.content,
            prompt_tokens=2,
            completion_tokens=self.completion_tokens,
            total_tokens=2 + self.completion_tokens,
            finish_reason="stop",
            raw={},
        )


async def test_latency_benchmark_runs_n_prompts_and_records_avg_tokens_per_sec():
    client = FakeApfelClient(content="hello", completion_tokens=4)
    bench = LatencyBenchmark(runs=3)

    result = await bench.run(client)

    assert result.benchmark == "latency"
    assert result.score == 1.0  # 1.0 = completed, not a quality measure
    assert len(client.requests) == 3
    assert result.metadata["runs"] == 3
    # prompt + completion tokens are aggregated
    assert result.metadata["total_prompt_tokens"] == 6
    assert result.metadata["total_completion_tokens"] == 12
    # tokens/sec should be a positive finite number
    assert result.metadata["tokens_per_sec"] > 0
    # duration covers all runs
    assert result.duration_ms >= 0


async def test_latency_benchmark_records_per_run_durations():
    client = FakeApfelClient(content="hi", completion_tokens=2, delay_ms=10)
    bench = LatencyBenchmark(runs=3)

    result = await bench.run(client)

    runs_meta = result.metadata["per_run_ms"]
    assert len(runs_meta) == 3
    # each run took at least the fake delay
    assert all(d >= 5 for d in runs_meta)  # allow a little scheduling slack


async def test_latency_benchmark_scores_zero_on_failure():
    class BoomClient:
        async def chat(self, request):
            raise RuntimeError("apfel down")

    bench = LatencyBenchmark(runs=1)
    result = await bench.run(BoomClient())

    assert result.score == 0.0
    assert "apfel down" in result.metadata["error"]


async def test_latency_benchmark_passes_runs_via_constructor():
    bench = LatencyBenchmark(runs=2)
    assert bench.runs == 2
