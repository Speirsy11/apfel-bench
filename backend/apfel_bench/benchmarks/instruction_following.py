"""Instruction-following benchmark.

Asks the model to reply within a word limit and scores 1.0 if the
response stays at or under the limit, else 0.0. This is a small, narrow
test of instruction adherence — extend with more constraints as needed.
"""

from __future__ import annotations

import time
from datetime import datetime

from apfel_bench.benchmark import Benchmark, BenchmarkResult, register
from apfel_bench.client import ChatMessage, ChatRequest


@register
class InstructionFollowingBenchmark:
    slug = "instruction_following"
    name = "Instruction following"
    description = "Asks the model to reply within a word limit and scores 1.0 if it does."

    DEFAULT_PROMPT = "Describe a fox in exactly 5 words."
    DEFAULT_MAX_WORDS = 5

    def __init__(self, prompt: str = DEFAULT_PROMPT, max_words: int = DEFAULT_MAX_WORDS):
        self.prompt = prompt
        self.max_words = max_words

    async def run(self, client) -> BenchmarkResult:
        started_at = datetime.now()
        t0 = time.perf_counter()

        request = ChatRequest(
            model="apple-foundationmodel",
            messages=[ChatMessage(role="user", content=self.prompt)],
        )
        response = await client.chat(request)
        finished_at = datetime.now()
        duration_ms = int((time.perf_counter() - t0) * 1000)

        word_count = len(response.content.split())
        score = 1.0 if word_count <= self.max_words else 0.0

        return BenchmarkResult(
            benchmark=self.slug,
            started_at=started_at,
            finished_at=finished_at,
            prompt=self.prompt,
            response=response.content,
            expected=f"<= {self.max_words} words",
            score=score,
            duration_ms=duration_ms,
            ttft_ms=None,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            metadata={
                "word_count": word_count,
                "max_words": self.max_words,
            },
        )
