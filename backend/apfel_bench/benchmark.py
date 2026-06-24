"""Benchmark protocol and result types.

A benchmark is anything that:
  * has a stable slug, name, description
  * can be run against an ApfelClient to produce a BenchmarkResult

The registry decorator lets new benchmarks self-register at import time,
so adding a benchmark is a one-class change in its own module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Protocol


@dataclass
class BenchmarkResult:
    benchmark: str
    started_at: datetime
    finished_at: datetime
    prompt: str
    response: str
    expected: Any | None
    score: float  # 0.0–1.0
    duration_ms: int
    ttft_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "prompt": self.prompt,
            "response": self.response,
            "expected": self.expected,
            "score": self.score,
            "duration_ms": self.duration_ms,
            "ttft_ms": self.ttft_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "metadata": self.metadata,
        }


class Benchmark(Protocol):
    slug: str
    name: str
    description: str

    async def run(self, client) -> BenchmarkResult: ...


_REGISTRY: dict[str, Benchmark] = {}


def register(cls: type) -> type:
    """Register a benchmark class. Use as @register on a class with a no-arg __init__.

    The class is instantiated once and stored. Benchmarks should be cheap to
    construct; if you need per-run state, stash it in run() and return it.
    """
    if not getattr(cls, "slug", None):
        raise ValueError("benchmark must define a non-empty 'slug'")
    if cls.slug in _REGISTRY:
        raise ValueError(f"benchmark slug already registered: {cls.slug!r}")
    _REGISTRY[cls.slug] = cls()
    return cls


def all_benchmarks() -> list[Benchmark]:
    """Return all registered benchmarks in stable (insertion) order."""
    return list(_REGISTRY.values())


def get(slug: str) -> Benchmark | None:
    return _REGISTRY.get(slug)
