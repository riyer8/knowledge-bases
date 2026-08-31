#!/bin/bash
# Start the Context Python backend if it is not already running.

set -e

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$REPO/.kb_backend.pid"
LOG="$REPO/.kb_backend.log"
PORT="${KB_PORT:-8765}"
PYTHON="${PYTHON:-python3}"
API_VERSION=2

if [ -f "$REPO/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO/.env"
  set +a
fi

health_check() {
  curl -sf "http://127.0.0.1:${PORT}/health" > /dev/null 2>&1
}

current_api_version() {
  curl -sf "http://127.0.0.1:${PORT}/health" 2>/dev/null \
    | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('api_version', 0))" 2>/dev/null \
    || echo 0
}

stop_backend() {
  if [ -f "$PID_FILE" ]; then
    OLD_PID="$(cat "$PID_FILE")"
    if kill -0 "$OLD_PID" 2>/dev/null; then
      kill "$OLD_PID" 2>/dev/null || true
      sleep 0.5
    fi
    rm -f "$PID_FILE"
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti:"${PORT}" 2>/dev/null | xargs kill 2>/dev/null || true
    sleep 0.3
  fi
}

if health_check && [ "$(current_api_version)" = "$API_VERSION" ]; then
  echo "already_running"
  exit 0
fi

stop_backend

cd "$REPO"
"$PYTHON" main.py >> "$LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"

for _ in $(seq 1 30); do
  if health_check; then
    echo "started"
    exit 0
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "failed"
    exit 1
  fi
  sleep 0.5
done

echo "failed"
exit 1
