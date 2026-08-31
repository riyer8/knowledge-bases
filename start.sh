#!/bin/bash
# Knowledge Base — one-click launcher
# Double-click this file (or run: bash start.sh) to start everything.

set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(command -v python3)"
LOG="$REPO/.kb_backend.log"
PID_FILE="$REPO/.kb_backend.pid"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step()  { echo -e "${GREEN}▶${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $1"; }
abort() { echo -e "${RED}✗${NC}  $1"; exit 1; }

echo ""
echo "  Context — starting up"
echo "  ─────────────────────────────"
echo ""

# ── 1. Python check ───────────────────────────────────────────────────────────
step "Checking Python..."
"$PYTHON" --version > /dev/null 2>&1 || abort "Python not found at $PYTHON. Edit PYTHON= in start.sh."

# ── 2. Python dependencies ────────────────────────────────────────────────────
step "Checking Python dependencies..."
MISSING=""
"$PYTHON" -c "import spacy" 2>/dev/null        || MISSING="$MISSING spacy"
"$PYTHON" -c "import dotenv" 2>/dev/null        || MISSING="$MISSING python-dotenv"

if [ -n "$MISSING" ]; then
    warn "Installing missing packages:$MISSING"
    "$PYTHON" -m pip install --quiet $MISSING
fi

# ── 3. spaCy model ────────────────────────────────────────────────────────────
step "Checking spaCy model..."
"$PYTHON" -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null || {
    warn "Downloading en_core_web_sm (one-time, ~50MB)..."
    "$PYTHON" -m spacy download en_core_web_sm --quiet
}

# ── 4. Ollama ─────────────────────────────────────────────────────────────────
step "Checking Ollama..."
if ! pgrep -x "ollama" > /dev/null; then
    warn "Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
fi

# Pull models if missing (shows progress inline)
OLLAMA_MODELS=$(ollama list 2>/dev/null || echo "")
if ! echo "$OLLAMA_MODELS" | grep -q "nomic-embed-text"; then
    warn "Pulling nomic-embed-text (~274MB, one-time)..."
    ollama pull nomic-embed-text
fi
if ! echo "$OLLAMA_MODELS" | grep -q "qwen2.5:3b"; then
    warn "Pulling qwen2.5:3b (~1.9GB, one-time)..."
    ollama pull qwen2.5:3b
fi

# ── 5. .env ───────────────────────────────────────────────────────────────────
if [ ! -f "$REPO/.env" ]; then
    warn "No .env found — copying from .env.example"
    cp "$REPO/.env.example" "$REPO/.env"
fi

# ── 6. Stop any old backend ───────────────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        step "Stopping previous backend (pid $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# ── 7. Start Python backend ───────────────────────────────────────────────────
step "Starting Python backend..."
cd "$REPO"
"$PYTHON" main.py >> "$LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"

# Wait for backend to be ready (up to 10s)
echo -n "   Waiting for backend"
for i in $(seq 1 20); do
    if curl -s http://127.0.0.1:8765/health > /dev/null 2>&1; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 0.5
done

if ! curl -s http://127.0.0.1:8765/health > /dev/null 2>&1; then
    echo ""
    warn "Backend didn't respond — check $LOG for errors"
fi

# ── 8. Open the Mac app ───────────────────────────────────────────────────────
step "Opening the app..."

# Look for a built .app — check common Xcode output locations
APP_PATH=""
for candidate in \
    "$REPO/DesktopApp/build/DerivedData/Build/Products/Debug/Context.app" \
    "$REPO/DesktopApp/build/DerivedData/Build/Products/Release/Context.app" \
    "$REPO/DesktopApp/build/Debug/Context.app" \
    "$REPO/DesktopApp/build/Release/Context.app" \
    "$HOME/Library/Developer/Xcode/DerivedData/DesktopApp-"*/Build/Products/Debug/Context.app \
    "$HOME/Library/Developer/Xcode/DerivedData/DesktopApp-"*/Build/Products/Release/Context.app
do
    if [ -d "$candidate" ]; then
        APP_PATH="$candidate"
        break
    fi
done

if [ -n "$APP_PATH" ]; then
    open "$APP_PATH"
    echo -e "   Opened: $APP_PATH"
else
    warn "App not built yet."
    echo ""
    echo "  ┌─────────────────────────────────────────────────────┐"
    echo "  │  One-time step: build the app in Xcode              │"
    echo "  │                                                       │"
    echo "  │  1. bash scripts/build_app.sh                        │"
    echo "  │     or open DesktopApp/DesktopApp.xcodeproj         │"
    echo "  │     and press ⌘B to build                           │"
    echo "  └─────────────────────────────────────────────────────┘"
    echo ""
    echo "  Opening Xcode now..."
    open "$REPO/DesktopApp/DesktopApp.xcodeproj"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${GREEN}All done.${NC}"
echo "  Backend log: $LOG"
echo "  To stop:     bash stop.sh"
echo ""
