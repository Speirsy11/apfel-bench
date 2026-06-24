#!/usr/bin/env bash
# Start the FastAPI backend and the Vite dev server together.
# Ctrl-C cleanly stops both.
#
# Env overrides:
#   APFEL_BENCH_PORT  backend port (default 8080)
#   VITE_PORT         frontend port (default 5173)
#
# Examples:
#   ./scripts/dev.sh
#   APFEL_BENCH_PORT=9000 ./scripts/dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV="$BACKEND/.venv"

APFEL_BENCH_PORT="${APFEL_BENCH_PORT:-8080}"
VITE_PORT="${VITE_PORT:-5173}"

# Pick the first available python3 to keep ALF happy.
PY_BIN="$(command -v python3)"
if [ ! -x "$VENV/bin/python" ]; then
  echo "→ creating venv at $VENV"
  /opt/homebrew/bin/python3 -m venv "$VENV" >/dev/null
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"
echo "→ installing backend deps (if needed)…"
pip install --quiet -e "$BACKEND[dev]"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "→ stopping…"
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ starting backend on 127.0.0.1:$APFEL_BENCH_PORT"
(
  cd "$BACKEND"
  APFEL_BENCH_HOST="127.0.0.1" \
  APFEL_BENCH_PORT="$APFEL_BENCH_PORT" \
    "$VENV/bin/python" -m uvicorn apfel_bench.main:app \
      --host 127.0.0.1 --port "$APFEL_BENCH_PORT" --reload
) &
BACKEND_PID=$!

# Brief wait so the backend log is shown above the Vite banner
sleep 1

echo "→ starting frontend on 127.0.0.1:$VITE_PORT"
(
  cd "$FRONTEND"
  bun run dev --port "$VITE_PORT" --host 127.0.0.1
) &
FRONTEND_PID=$!

echo ""
echo "  backend:  http://127.0.0.1:$APFEL_BENCH_PORT/"
echo "  frontend: http://127.0.0.1:$VITE_PORT/"
echo "  api docs: http://127.0.0.1:$APFEL_BENCH_PORT/docs"
echo ""
echo "Press Ctrl-C to stop both."

wait
