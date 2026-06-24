"""Default app composition and uvicorn entry point.

Config is read from environment variables, with the apfel Bearer token
falling back to the macOS Keychain entry written by `scripts/start-apfel.sh`.

    APFEL_URL          default http://127.0.0.1:11435/v1
    APFEL_TOKEN        Bearer token; falls back to Keychain
    APFEL_BENCH_DB     default ../data/results.sqlite (relative to backend/)
    APFEL_BENCH_HOST   default 127.0.0.1
    APFEL_BENCH_PORT   default 8080
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from apfel_bench.api import create_app
from apfel_bench.client import HttpApfelClient
from apfel_bench.storage import SqliteStorage


def _token_from_keychain() -> str | None:
    try:
        return subprocess.check_output(
            [
                "security",
                "find-generic-password",
                "-a",
                "value",
                "-s",
                "openclaw/apfel/token",
                "-w",
            ],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return None


def load_config() -> tuple[str, str | None, Path]:
    apfel_url = os.environ.get("APFEL_URL", "http://127.0.0.1:11435/v1")
    apfel_token = os.environ.get("APFEL_TOKEN") or _token_from_keychain()
    db_path = Path(os.environ.get("APFEL_BENCH_DB", str(Path(__file__).resolve().parent.parent.parent / "data" / "results.sqlite")))
    return apfel_url, apfel_token, db_path


def create_default_app():
    url, token, db = load_config()
    client = HttpApfelClient(base_url=url, token=token)
    storage = SqliteStorage(db)
    return create_app(client=client, storage=storage)


app = create_default_app()


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("APFEL_BENCH_HOST", "127.0.0.1")
    port = int(os.environ.get("APFEL_BENCH_PORT", "8080"))
    uvicorn.run("apfel_bench.main:app", host=host, port=port, reload=True)
