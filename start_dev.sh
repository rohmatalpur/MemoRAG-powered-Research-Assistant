#!/usr/bin/env bash
# Start all services for local development (without Docker)
# Prerequisites: Python 3.11+, Node 20+, Qdrant running, Redis running, Grobid running (optional)

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Personal Research Assistant — Dev Start ==="

# Create .env if it doesn't exist
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created .env — please fill in your API keys before continuing."
  exit 1
fi

# Create data dirs
mkdir -p "$ROOT/data/papers"

# ── Backend ──────────────────────────────────────────────────
echo ""
echo "[1/3] Starting FastAPI backend on :8000 ..."
cd "$ROOT"
pip install -q -r backend/requirements.txt

# Backend in background
PYTHONPATH="$ROOT" uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "    Backend PID: $BACKEND_PID"

# ── Celery worker ─────────────────────────────────────────────
echo ""
echo "[2/3] Starting Celery worker ..."
PYTHONPATH="$ROOT" celery -A backend.tasks worker --loglevel=info --concurrency=2 &
WORKER_PID=$!
echo "    Worker PID: $WORKER_PID"

# ── Frontend ──────────────────────────────────────────────────
echo ""
echo "[3/3] Starting Next.js frontend on :3000 ..."
cd "$ROOT/frontend"
npm install --silent
npm run dev &
FRONTEND_PID=$!
echo "    Frontend PID: $FRONTEND_PID"

echo ""
echo "=== All services started ==="
echo "    Frontend:  http://localhost:3000"
echo "    Backend:   http://localhost:8000"
echo "    API docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for any process to exit
trap "kill $BACKEND_PID $WORKER_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
