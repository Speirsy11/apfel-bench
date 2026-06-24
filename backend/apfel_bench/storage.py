"""SQLite persistence for benchmark results and chat history.

Single-file DB at the path the caller chooses. Sync calls — wrap with
`asyncio.to_thread` if you need to call from async code.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from apfel_bench.benchmark import BenchmarkResult


class SqliteStorage:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    id TEXT PRIMARY KEY,
                    benchmark TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    prompt TEXT,
                    response TEXT,
                    expected TEXT,
                    score REAL,
                    duration_ms INTEGER,
                    ttft_ms INTEGER,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    metadata TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_results_benchmark ON results(benchmark)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_results_started_at ON results(started_at)")

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at)")
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")

    def save(self, result: BenchmarkResult) -> str:
        run_id = uuid.uuid4().hex
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO results (
                    id, benchmark, started_at, finished_at, prompt, response,
                    expected, score, duration_ms, ttft_ms, prompt_tokens,
                    completion_tokens, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    result.benchmark,
                    result.started_at.isoformat(),
                    result.finished_at.isoformat(),
                    result.prompt,
                    result.response,
                    json.dumps(result.expected) if result.expected is not None else None,
                    result.score,
                    result.duration_ms,
                    result.ttft_ms,
                    result.prompt_tokens,
                    result.completion_tokens,
                    json.dumps(result.metadata),
                ),
            )
        return run_id

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM results WHERE id = ?", (run_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, benchmark: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            if benchmark:
                rows = c.execute(
                    "SELECT * FROM results WHERE benchmark = ? ORDER BY started_at DESC LIMIT ?",
                    (benchmark, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM results ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["expected"] = json.loads(d["expected"]) if d["expected"] else None
        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
        return d

    # ---- chat ----

    def create_chat_session(self, title: str | None = None) -> str:
        from datetime import datetime as _dt
        import uuid as _uuid

        sid = _uuid.uuid4().hex
        now = _dt.now().isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (sid, title, now, now),
            )
        return sid

    def touch_chat_session(self, session_id: str) -> None:
        from datetime import datetime as _dt

        with self._conn() as c:
            c.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (_dt.now().isoformat(), session_id),
            )

    def rename_chat_session(self, session_id: str, title: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE chat_sessions SET title = ? WHERE id = ?",
                (title, session_id),
            )

    def add_chat_message(self, session_id: str, role: str, content: str) -> int:
        from datetime import datetime as _dt

        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, _dt.now().isoformat()),
            )
        self.touch_chat_session(session_id)
        return cur.lastrowid

    def list_chat_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_chat_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]
