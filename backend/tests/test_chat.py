"""Chat history: sessions + messages tables, plus the streaming endpoint."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apfel_bench.api import create_app
from apfel_bench.client import ChatRequest, ChatResponse
from apfel_bench.storage import SqliteStorage


class FakeApfelClient:
    def __init__(self, response: str = "Hi from the model."):
        self.response = response
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            content=self.response,
            prompt_tokens=5,
            completion_tokens=4,
            total_tokens=9,
            finish_reason="stop",
            raw={},
        )

    async def aclose(self) -> None:
        pass


def _client(response: str = "Hi from the model."):
    fake = FakeApfelClient(response=response)
    store = SqliteStorage(Path(tempfile.mkdtemp()) / "results.sqlite")
    app = create_app(client=fake, storage=store)
    return TestClient(app), fake, store


def test_storage_creates_chat_tables_idempotently():
    from apfel_bench.storage import SqliteStorage

    with tempfile.TemporaryDirectory() as d:
        store = SqliteStorage(Path(d) / "results.sqlite")
        sid = store.create_chat_session(title="hello")
        store.add_chat_message(sid, role="user", content="hi")
        store.add_chat_message(sid, role="assistant", content="hello there")

        msgs = store.list_chat_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "hello there"


def test_storage_lists_chat_sessions_newest_first():
    from apfel_bench.storage import SqliteStorage

    with tempfile.TemporaryDirectory() as d:
        store = SqliteStorage(Path(d) / "results.sqlite")
        a = store.create_chat_session(title="first")
        b = store.create_chat_session(title="second")
        store.add_chat_message(a, role="user", content="a user msg")
        store.add_chat_message(b, role="user", content="b user msg")

        sessions = store.list_chat_sessions()
        assert len(sessions) == 2
        assert sessions[0]["id"] == b  # newest first
        assert sessions[0]["title"] == "second"


def test_post_chat_sends_messages_to_apfel_and_returns_reply():
    http, fake, _ = _client(response="hello there")
    r = http.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "hello there"
    assert body["session_id"]
    # apfel got our message
    assert fake.requests[0].messages[0].content == "hi"


def test_post_chat_persists_user_and_assistant_messages():
    http, _, store = _client(response="hello there")
    r = http.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    body = r.json()
    msgs = store.list_chat_messages(body["session_id"])
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "hi"
    assert msgs[1]["content"] == "hello there"


def test_post_chat_with_existing_session_id_appends_in_place():
    http, fake, store = _client(response="hi")
    # First turn
    r1 = http.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "first"}]},
    )
    sid = r1.json()["session_id"]
    # Second turn uses the same session
    r2 = http.post(
        "/api/chat",
        json={"session_id": sid, "messages": [{"role": "user", "content": "second"}]},
    )
    assert r2.json()["session_id"] == sid
    msgs = store.list_chat_messages(sid)
    assert [m["content"] for m in msgs] == ["first", "hi", "second", "hi"]


def test_get_chat_sessions_lists_sessions_with_titles():
    http, _, _ = _client(response="reply")
    http.post("/api/chat", json={"messages": [{"role": "user", "content": "what is 2+2?"}]})
    r = http.get("/api/chat/sessions")
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) == 1
    assert "what is 2+2" in sessions[0]["title"]


def test_get_chat_session_messages_returns_full_history():
    http, _, _ = _client(response="ok")
    post = http.post("/api/chat", json={"messages": [{"role": "user", "content": "ping"}]}).json()
    sid = post["session_id"]
    r = http.get(f"/api/chat/sessions/{sid}/messages")
    assert r.status_code == 200
    msgs = r.json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]


def test_post_chat_uses_session_title_from_first_user_message():
    http, _, store = _client(response="ok")
    post = http.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "What is the capital of Austria?"}]},
    )
    sid = post.json()["session_id"]
    sessions = store.list_chat_sessions()
    assert sessions[0]["id"] == sid
    assert "capital of austria" in sessions[0]["title"].lower()
