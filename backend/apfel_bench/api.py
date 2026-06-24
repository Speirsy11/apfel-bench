"""FastAPI app factory and routes.

The app is created via `create_app(client, storage)` so tests can inject
fakes. The default composition (real apfel client, real sqlite) lives in
`apfel_bench.main`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from apfel_bench.benchmark import all_benchmarks, get as get_benchmark
from apfel_bench.client import ApfelClient
from apfel_bench.storage import SqliteStorage

# Importing the benchmarks package runs the @register decorators so
# the registry is populated before any route handler is called.
import apfel_bench.benchmarks  # noqa: F401


def create_app(*, client: ApfelClient, storage: SqliteStorage) -> FastAPI:
    app = FastAPI(title="apfel-bench", version="0.1.0")
    app.state.apfel = client
    app.state.storage = storage

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/benchmarks")
    def list_benchmarks() -> list[dict[str, Any]]:
        return [
            {"slug": b.slug, "name": b.name, "description": b.description}
            for b in all_benchmarks()
        ]

    @app.post("/api/benchmarks/{slug}/run")
    async def run_benchmark(slug: str) -> dict[str, Any]:
        bench = get_benchmark(slug)
        if bench is None:
            raise HTTPException(status_code=404, detail=f"unknown benchmark: {slug!r}")
        result = await bench.run(app.state.apfel)
        run_id = app.state.storage.save(result)
        payload = result.to_dict()
        payload["run_id"] = run_id
        return payload

    @app.get("/api/results")
    def list_results(benchmark: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        rows = app.state.storage.list(benchmark=benchmark, limit=limit)
        # Make id visible as run_id for symmetry with the run response
        for r in rows:
            r.setdefault("run_id", r.get("id"))
        return rows

    @app.get("/api/results/{run_id}")
    def get_result(run_id: str) -> dict[str, Any]:
        row = app.state.storage.get(run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="not found")
        row.setdefault("run_id", row.get("id"))
        return row

    @app.post("/api/chat")
    async def post_chat(payload: dict) -> dict[str, Any]:
        """Send a chat turn to apfel, persist it, return the reply + session id.

        Body: {"session_id"?: str, "messages": [{"role": str, "content": str}, ...]}
        """
        from apfel_bench.client import ChatMessage, ChatRequest

        session_id = payload.get("session_id")
        raw_messages = payload.get("messages") or []
        if not raw_messages:
            raise HTTPException(status_code=400, detail="messages must be a non-empty list")

        messages = [ChatMessage(role=m["role"], content=m["content"]) for m in raw_messages]

        # If client didn't supply a session id, start a new one and use the
        # first user message as the session title.
        if not session_id:
            session_id = app.state.storage.create_chat_session()
            first_user = next((m.content for m in messages if m.role == "user"), None)
            if first_user:
                title = first_user.strip().splitlines()[0][:60].strip()
                if title:
                    app.state.storage.rename_chat_session(session_id, title)

        # Persist the new user messages from this turn.
        for m in messages:
            app.state.storage.add_chat_message(session_id, m.role, m.content)

        request = ChatRequest(model="apple-foundationmodel", messages=messages)
        response = await app.state.apfel.chat(request)
        app.state.storage.add_chat_message(session_id, "assistant", response.content)

        return {
            "session_id": session_id,
            "reply": response.content,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
        }

    @app.get("/api/chat/sessions")
    def list_chat_sessions(limit: int = 50) -> list[dict[str, Any]]:
        return app.state.storage.list_chat_sessions(limit=limit)

    @app.get("/api/chat/sessions/{session_id}/messages")
    def list_chat_messages(session_id: str) -> list[dict[str, Any]]:
        return app.state.storage.list_chat_messages(session_id)

    return app
