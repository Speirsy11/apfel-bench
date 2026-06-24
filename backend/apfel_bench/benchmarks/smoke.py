"""Smoke benchmark.

Asks the model to reply with the single word 'pong' and scores 1.0 if
the response contains that token (case-insensitive), else 0.0. The score
is secondary to the real job of this benchmark: proving the path
benchmark -> ApfelClient -> BenchmarkResult works end-to-end.
"""

from __future__ import annotations

import time
from datetime import datetime

from apfel_bench.benchmark import Benchmark, BenchmarkResult, register
from apfel_bench.client import ChatMessage, ChatRequest


@register
class SmokeBenchmark:
    slug = "smoke"
    name = "Smoke"
    description = "Asks the model to reply with 'pong' and scores 1.0 if the token appears."

    PROMPT = "Reply with only the single word: pong"
    EXPECTED = "pong"

    async def run(self, client) -> BenchmarkResult:
        started_at = datetime.now()
        t0 = time.perf_counter()

        request = ChatRequest(
            model="apple-foundationmodel",
            messages=[ChatMessage(role="user", content=self.PROMPT)],
        )
        response = await client.chat(request)

        finished_at = datetime.now()
        duration_ms = int((time.perf_counter() - t0) * 1000)

        score = 1.0 if self.EXPECTED.lower() in response.content.lower() else 0.0

        return BenchmarkResult(
            benchmark=self.slug,
            started_at=started_at,
            finished_at=finished_at,
            prompt=self.PROMPT,
            response=response.content,
            expected=self.EXPECTED,
            score=score,
            duration_ms=duration_ms,
            ttft_ms=None,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            metadata={},
        )
