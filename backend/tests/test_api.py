"""HTTP API for benchmarks, results, and chat."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apfel_bench.api import create_app
from apfel_bench.benchmark import BenchmarkResult
from apfel_bench.benchmarks.smoke import SmokeBenchmark
from apfel_bench.client import ChatRequest, ChatResponse
from apfel_bench.storage import SqliteStorage


class FakeApfelClient:
    def __init__(self, content: str = "pong"):
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

    async def aclose(self) -> None:
        pass


def _client(content: str = "pong"):
    fake = FakeApfelClient(content=content)
    store = SqliteStorage(Path(tempfile.mkdtemp()) / "results.sqlite")
    app = create_app(client=fake, storage=store)
    return TestClient(app), fake, store


def test_health_endpoint_returns_ok():
    http, _, _ = _client()
    r = http.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_benchmarks_includes_registered_ones():
    http, _, _ = _client()
    r = http.get("/api/benchmarks")
    assert r.status_code == 200
    slugs = {b["slug"] for b in r.json()}
    assert "smoke" in slugs


def test_run_benchmark_executes_and_persists_result():
    http, fake, store = _client(content="pong!")
    r = http.post("/api/benchmarks/smoke/run")
    assert r.status_code == 200
    body = r.json()
    assert body["benchmark"] == "smoke"
    assert body["score"] == 1.0
    assert "run_id" in body
    assert body["response"] == "pong!"
    # Persisted
    assert store.get(body["run_id"]) is not None


def test_run_unknown_benchmark_returns_404():
    http, _, _ = _client()
    r = http.post("/api/benchmarks/does_not_exist/run")
    assert r.status_code == 404


def test_list_results_returns_recent_runs_in_reverse_order():
    http, fake, store = _client(content="pong")
    http.post("/api/benchmarks/smoke/run")
    http.post("/api/benchmarks/smoke/run")
    r = http.get("/api/results")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    # Most recent first
    assert rows[0]["started_at"] >= rows[1]["started_at"]


def test_get_result_by_id_returns_full_payload():
    http, _, _ = _client(content="pong")
    run = http.post("/api/benchmarks/smoke/run").json()
    r = http.get(f"/api/results/{run['run_id']}")
    assert r.status_code == 200
    assert r.json()["run_id" if "run_id" in r.json() else "id"] or r.json()["id"] == run["run_id"]
