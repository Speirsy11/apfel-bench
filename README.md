# apfel-bench

Benchmarks, chat, and results dashboard for Apple's on-device FoundationModel via [apfel](https://github.com/Arthur-Ficial/apfel).

100% on-device. No API keys, no cloud, no data leaves the Mac.

## What it does

- Runs a suite of benchmarks against the Apple FoundationModel (3B on-device LLM shipped in macOS 26+)
- Streams chat with the model from a web UI, with TTFT measurement
- Persists results and chat history in a local SQLite database
- Surfaces everything through a small web dashboard with a per-run latency chart for the `latency` benchmark
- Ships a reusable SSE streaming pattern you can copy into any project that talks to an OpenAI-compatible server (apfel, Ollama, vLLM, llama.cpp, OpenAI itself)

## Requirements

- macOS 26+ on Apple Silicon
- Apple Intelligence enabled in System Settings
- [apfel](https://github.com/Arthur-Ficial/apfel) installed: `brew install apfel`
- Python 3.11+
- Bun (for the frontend)

## Quick start

```bash
# 1. install deps + start apfel on a free port (11435 by default; 11434 collides with Ollama)
make install
./scripts/start-apfel.sh       # or: APFEL_PORT=11435 brew services start apfel

# 2. start the dev stack (backend on 8080, frontend on 5173, live reload, Ctrl-C stops both)
make dev
# → http://127.0.0.1:5173
# → http://127.0.0.1:8080/docs  (FastAPI Swagger)
```

If you don't have `make`, the same commands live in `scripts/dev.sh`.

## Layout

```
backend/    FastAPI service, benchmark suite, SQLite store, streaming chat proxy
frontend/   React + Vite + Bun dashboard
data/       results.sqlite, chat history (gitignored)
scripts/    start/stop helpers for apfel and the dev stack
Makefile    install / test / dev / stop / clean
```

## Built-in benchmarks

| slug             | what it measures                                          |
|------------------|-----------------------------------------------------------|
| `smoke`          | can apfel answer one short question without error?        |
| `latency`        | mean / p50 / p95 / max duration over N runs, plus tok/s   |
| `json_shape`     | does the response parse as the requested JSON shape?      |
| `instruction_following` | hits a word-count target while hitting 3 must-mention constraints |
| `factual_qa`     | 10 multiple-choice questions, A–D                        |

Each benchmark lives in `backend/apfel_bench/benchmarks/<slug>.py` with a matching `tests/test_<slug>.py`.

## Adding a benchmark

Subclass `apfel_bench.benchmark.Benchmark` (or implement the same shape) and register it with `@register`:

```python
from apfel_bench.benchmark import BenchmarkResult, register

@register
class MyBenchmark:
    slug = "my_bench"
    name = "My benchmark"
    description = "Does a thing."

    async def run(self, client):
        # call client.chat(...) to talk to apfel
        # return a BenchmarkResult with a score in 0.0–1.0
        ...
```

Then add `from apfel_bench.benchmarks import my_bench  # noqa: F401` to `backend/apfel_bench/benchmarks/__init__.py` so the `@register` decorator fires at startup.

The new benchmark shows up in `GET /api/benchmarks`, the dashboard's Benchmarks tab, and `POST /api/benchmarks/{slug}/run` automatically.

## Reusable SSE streaming pattern

The chat pipeline is built from two pure async-iterator transforms that you can lift into any project:

```python
# Python side — apfel_bench/streaming.py
async def sse_decode_bytes(byte_stream):  # bytes -> SSE data payloads
    """Drops [DONE], empty, retry, comments. Handles events split across chunks."""

async def openai_chat_chunks(payload_stream):  # data payloads -> ChatChunk
    """Parses choices[0].delta.content and finish_reason. Works for any OpenAI-compatible API."""

# Compose them:
async for chunk in openai_chat_chunks(sse_decode_bytes(resp.aiter_bytes())):
    ...
```

```ts
// JS side — frontend/src/sse.ts
export async function* parseSSE<T>(response: Response): AsyncGenerator<T> {
  // mirrors sse_decode_bytes: TextDecoder, \n\n boundary, [DONE] skip, JSON.parse
}
```

The pattern was inspired by [opencode](https://github.com/anomalyco/opencode)'s split between `Framing.sse` (transport concern) and `Protocol.openai_chat` (chunk-shape concern) in `packages/llm/src/`. Keeping the two independent means the same SSE parser can feed Anthropic, OpenAI, Bedrock, or any other provider that exposes an OpenAI-compatible chat-completions endpoint — only the `Protocol` part needs to be swapped.

The server-side endpoint `POST /api/chat/stream` and the client `streamChat()` are the wiring that ties the two halves together, plus a `chunk` / `done` / `error` event protocol on top. See `backend/apfel_bench/streaming.py` for the full docstring.

## Tests

```bash
make test           # 68 backend + 21 frontend unit tests
make test-live      # 2 live integration tests against a running apfel
```

## License

MIT.
