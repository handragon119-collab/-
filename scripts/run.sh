#!/usr/bin/env bash
# Run JARVIS: FastAPI backend + Vite frontend, then open Chrome.
# Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  echo "No .venv found — run ./scripts/setup.sh first." >&2
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "→ Starting backend (https://localhost:8340)…"
python server.py &

echo "→ Starting frontend (http://localhost:5173)…"
( cd frontend && npm run dev ) &

sleep 3
if command -v open >/dev/null 2>&1; then
  open -a "Google Chrome" "http://localhost:5173" || open "http://localhost:5173"
fi

wait
