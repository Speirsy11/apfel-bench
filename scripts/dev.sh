#!/usr/bin/env bash
# Start backend (FastAPI) and frontend (Vite) together.
# Ctrl-C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cleanup() {
  echo ""
  echo "stopping…"
  kill "${BACKEND_PID:-0}" "${FRONTEND_PID:-0}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  /opt/homebrew/bin/python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet -e ".[dev]"

cd "$ROOT"

# Backend
source .venv/bin/activate 2>/dev/null || true
cd "$ROOT/backend"
APFEL_BENCH_HOST="${APFEL_BENCH_HOST:-127.0.0.1}" \
APFEL_BENCH_PORT="${APFEL_BENCH_PORT:-8080}" \
  uvicorn apfel_bench.main:app --host 127.0.0.1 --port "${APFEL_BENCH_PORT:-8080}" --reload &
BACKEND_PID=$!

# Frontend
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  bun install
fi
bun run dev &
FRONTEND_PID=$!

echo ""
echo "backend  http://127.0.0.1:${APFEL_BENCH_PORT:-8080}"
echo "frontend http://127.0.0.1:5173"
echo ""
wait
