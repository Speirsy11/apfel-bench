"""Latency benchmark.

Runs a fixed prompt N times and records total / per-run duration and
aggregate tokens/sec. Score is 1.0 if all runs succeed, 0.0 if any fail.
This is a perf metric, not a quality one — the dashboard reads the
metadata to plot it.
"""

from __future__ import annotations

import time
from datetime import datetime

from apfel_bench.benchmark import Benchmark, BenchmarkResult, register
from apfel_bench.client import ChatMessage, ChatRequest


@register
class LatencyBenchmark:
    slug = "latency"
    name = "Latency"
    description = "Runs a short prompt N times and reports tokens/sec and per-run duration."

    PROMPT = "Reply with a single word: hi"
    DEFAULT_RUNS = 5

    def __init__(self, runs: int = DEFAULT_RUNS):
        self.runs = runs

    async def run(self, client) -> BenchmarkResult:
        started_at = datetime.now()
        t0 = time.perf_counter()

        per_run_ms: list[float] = []
        total_prompt = 0
        total_completion = 0
        last_response = ""
        error: str | None = None

        try:
            for _ in range(self.runs):
                run_t0 = time.perf_counter()
                resp = await client.chat(
                    ChatRequest(
                        model="apple-foundationmodel",
                        messages=[ChatMessage(role="user", content=self.PROMPT)],
                    )
                )
                per_run_ms.append((time.perf_counter() - run_t0) * 1000)
                total_prompt += resp.prompt_tokens
                total_completion += resp.completion_tokens
                last_response = resp.content
            score = 1.0
        except Exception as e:
            error = repr(e)
            score = 0.0

        finished_at = datetime.now()
        duration_ms = int((time.perf_counter() - t0) * 1000)
        elapsed_sec = duration_ms / 1000 if duration_ms else 0.001
        tokens_per_sec = total_completion / elapsed_sec if elapsed_sec > 0 else 0.0

        return BenchmarkResult(
            benchmark=self.slug,
            started_at=started_at,
            finished_at=finished_at,
            prompt=self.PROMPT,
            response=last_response,
            expected=None,
            score=score,
            duration_ms=duration_ms,
            ttft_ms=None,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            metadata={
                "runs": self.runs,
                "per_run_ms": per_run_ms,
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_completion,
                "tokens_per_sec": tokens_per_sec,
                "error": error,
            },
        )
