# apfel-bench

Benchmarks, chat, and results dashboard for Apple's on-device FoundationModel via [apfel](https://github.com/Arthur-Ficial/apfel).

100% on-device. No API keys, no cloud, no data leaves the Mac.

## What it does

- Runs a suite of benchmarks against the Apple FoundationModel (3B on-device LLM shipped in macOS 26+)
- Streams chat with the model from a web UI
- Persists results and chat history in a local SQLite database
- Surfaces everything through a small web dashboard

## Requirements

- macOS 26+ on Apple Silicon
- Apple Intelligence enabled in System Settings
- [apfel](https://github.com/Arthur-Ficial/apfel) installed: `brew install apfel`
- Python 3.11+
- Bun (for the frontend)

## Quick start

```bash
# 1. start apfel on a free port (anything other than 11434 if you run Ollama)
APFEL_PORT=11435 brew services start apfel
# or use the project's LaunchAgent
./scripts/start-apfel.sh

# 2. backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn apfel_bench.api:app --reload --port 8080

# 3. frontend (separate terminal)
cd frontend
bun install
bun run dev
```

Open <http://localhost:5173>.

## Layout

```
backend/    FastAPI service, benchmark suite, SQLite store, chat proxy
frontend/   React + Vite + Bun dashboard
data/       results.sqlite, chat history (gitignored)
scripts/    start/stop helpers for apfel and the dev stack
```

## Adding a benchmark

Subclass `apfel_bench.benchmark.Benchmark` (or implement the same shape) and
register it with `@register`:

```python
from apfel_bench.benchmark import Benchmark, BenchmarkResult, register

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

The new benchmark shows up in `GET /api/benchmarks`, the dashboard's
"Benchmarks" tab, and `/api/benchmarks/{slug}/run` automatically.

## License

MIT.
