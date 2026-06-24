"""Tests for POST /api/chat/stream — SSE proxy of apfel streaming + persistence."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from apfel_bench.api import create_app
from apfel_bench.client import ChatMessage, ChatRequest, ChatResponse
from apfel_bench.storage import SqliteStorage


class FakeStreamingClient:
    """In-memory client whose stream_chat yields the chunks you give it."""

    def __init__(self, deltas: list[str], finish_reason: str = "stop"):
        self.deltas = deltas
        self.finish_reason = finish_reason
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            content="".join(self.deltas),
            prompt_tokens=2,
            completion_tokens=len(self.deltas),
            total_tokens=2 + len(self.deltas),
            finish_reason="stop",
            raw={},
        )

    async def stream_chat(self, request: ChatRequest):
        from apfel_bench.streaming import ChatChunk

        self.requests.append(request)
        for d in self.deltas:
            yield ChatChunk(content_delta=d, finish_reason=None, raw={})
        yield ChatChunk(content_delta="", finish_reason=self.finish_reason, raw={})

    async def aclose(self) -> None:
        pass


def _client(deltas: list[str], finish_reason: str = "stop"):
    fake = FakeStreamingClient(deltas, finish_reason=finish_reason)
    store = SqliteStorage(Path(tempfile.mkdtemp()) / "results.sqlite")
    app = create_app(client=fake, storage=store)
    return TestClient(app), fake, store


def test_stream_endpoint_returns_text_event_stream_content_type():
    http, _, _ = _client(deltas=["hi", " there"])
    with http.stream(
        "POST",
        "/api/chat/stream",
        json={"messages": [{"role": "user", "content": "hello"}]},
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        # Drain
        for _ in r.iter_lines():
            pass


def test_stream_endpoint_emits_chunk_events_with_content_deltas():
    http, _, _ = _client(deltas=["Hel", "lo", " world"])
    with http.stream(
        "POST",
        "/api/chat/stream",
        json={"messages": [{"role": "user", "content": "hi"}]},
    ) as r:
        events: list[dict] = []
        for line in r.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    # Should have one chunk event per delta + one done event
    chunk_events = [e for e in events if e.get("type") == "chunk"]
    done_events = [e for e in events if e.get("type") == "done"]
    assert [c["content"] for c in chunk_events] == ["Hel", "lo", " world"]
    assert len(done_events) == 1
    assert done_events[0]["full_response"] == "Hello world"
    assert done_events[0]["session_id"]


def test_stream_endpoint_persists_user_and_full_assistant_reply():
    http, _, store = _client(deltas=["Hel", "lo"])
    with http.stream(
        "POST",
        "/api/chat/stream",
        json={"messages": [{"role": "user", "content": "greet me"}]},
    ) as r:
        done = None
        for line in r.iter_lines():
            if line.startswith("data: ") and '"done"' in line:
                done = json.loads(line[6:])
                break

    sid = done["session_id"]
    msgs = store.list_chat_messages(sid)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "greet me"
    assert msgs[1]["content"] == "Hello"  # concatenated from deltas


def test_stream_endpoint_appends_to_existing_session():
    http, _, store = _client(deltas=["a", "b"])
    # First call creates a session
    with http.stream(
        "POST",
        "/api/chat/stream",
        json={"messages": [{"role": "user", "content": "first"}]},
    ) as r:
        for line in r.iter_lines():
            if line.startswith("data: ") and '"done"' in line:
                sid = json.loads(line[6:])["session_id"]
                break
    # Second call uses the same session
    with http.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": sid, "messages": [{"role": "user", "content": "second"}]},
    ) as r:
        for line in r.iter_lines():
            if line.startswith("data: ") and '"done"' in line:
                break

    msgs = store.list_chat_messages(sid)
    assert [m["content"] for m in msgs] == ["first", "ab", "second", "ab"]


def test_stream_endpoint_records_finish_reason_in_done_event():
    http, _, _ = _client(deltas=["x"], finish_reason="length")
    with http.stream(
        "POST",
        "/api/chat/stream",
        json={"messages": [{"role": "user", "content": "hi"}]},
    ) as r:
        done = None
        for line in r.iter_lines():
            if line.startswith("data: ") and '"done"' in line:
                done = json.loads(line[6:])
                break
    assert done["finish_reason"] == "length"


def test_stream_endpoint_rejects_empty_messages():
    http, _, _ = _client(deltas=["x"])
    r = http.post("/api/chat/stream", json={"messages": []})
    assert r.status_code == 400
