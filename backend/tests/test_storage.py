"""SQLite persistence for benchmark results and chat history."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from apfel_bench.benchmark import BenchmarkResult


def _make_result(benchmark: str = "smoke", score: float = 1.0, response: str = "pong") -> BenchmarkResult:
    now = datetime.now()
    return BenchmarkResult(
        benchmark=benchmark,
        started_at=now,
        finished_at=now,
        prompt="Reply with only the single word: pong",
        response=response,
        expected="pong",
        score=score,
        duration_ms=420,
        ttft_ms=None,
        prompt_tokens=7,
        completion_tokens=3,
        metadata={"note": "ok"},
    )


def test_storage_saves_and_retrieves_a_result_by_id():
    from apfel_bench.storage import SqliteStorage

    with tempfile.TemporaryDirectory() as d:
        store = SqliteStorage(Path(d) / "results.sqlite")
        result = _make_result()

        run_id = store.save(result)
        fetched = store.get(run_id)

        assert fetched is not None
        assert fetched["benchmark"] == "smoke"
        assert fetched["score"] == 1.0
        assert fetched["response"] == "pong"
        assert fetched["prompt_tokens"] == 7
        assert fetched["completion_tokens"] == 3
        assert fetched["metadata"] == {"note": "ok"}


def test_storage_list_returns_recent_results_first():
    from apfel_bench.storage import SqliteStorage

    with tempfile.TemporaryDirectory() as d:
        store = SqliteStorage(Path(d) / "results.sqlite")
        for i in range(3):
            store.save(_make_result(response=f"r{i}"))

        rows = store.list()

        assert len(rows) == 3
        # ORDER BY started_at DESC
        assert rows[0]["response"] == "r2"
        assert rows[-1]["response"] == "r0"


def test_storage_list_filters_by_benchmark_slug():
    from apfel_bench.storage import SqliteStorage

    with tempfile.TemporaryDirectory() as d:
        store = SqliteStorage(Path(d) / "results.sqlite")
        store.save(_make_result(benchmark="smoke", response="s1"))
        store.save(_make_result(benchmark="smoke", response="s2"))
        store.save(_make_result(benchmark="latency", response="l1"))

        smoke_rows = store.list(benchmark="smoke")
        latency_rows = store.list(benchmark="latency")

        assert len(smoke_rows) == 2
        assert {r["response"] for r in smoke_rows} == {"s1", "s2"}
        assert len(latency_rows) == 1
        assert latency_rows[0]["response"] == "l1"


def test_storage_creates_parent_directory_and_is_idempotent():
    from apfel_bench.storage import SqliteStorage

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "nested" / "results.sqlite"
        store1 = SqliteStorage(path)
        store1.save(_make_result())

        # Open again — schema should already exist
        store2 = SqliteStorage(path)
        rows = store2.list()
        assert len(rows) == 1


def test_storage_handles_none_expected_and_empty_metadata():
    from apfel_bench.storage import SqliteStorage

    with tempfile.TemporaryDirectory() as d:
        store = SqliteStorage(Path(d) / "results.sqlite")
        result = _make_result()
        result.expected = None
        result.metadata = {}

        run_id = store.save(result)
        fetched = store.get(run_id)

        assert fetched["expected"] is None
        assert fetched["metadata"] == {}


def test_storage_get_returns_none_for_unknown_id():
    from apfel_bench.storage import SqliteStorage

    with tempfile.TemporaryDirectory() as d:
        store = SqliteStorage(Path(d) / "results.sqlite")
        assert store.get("nope") is None
