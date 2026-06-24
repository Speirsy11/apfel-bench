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
