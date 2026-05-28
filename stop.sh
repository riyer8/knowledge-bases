#!/bin/bash
# Stops the Knowledge Base backend.

REPO="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$REPO/.kb_backend.pid"

GREEN='\033[0;32m'
NC='\033[0m'

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo -e "${GREEN}▶${NC} Backend stopped (pid $PID)."
    else
        echo "Backend was not running."
    fi
    rm -f "$PID_FILE"
else
    echo "No backend pid file found."
fi
