#!/bin/bash
# Build Context and install it to /Applications like a normal Mac app.
#
# Usage:
#   bash scripts/install_app.sh
#
# After install, open from Applications or Spotlight: "Context"

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Context"
APP_DEST="/Applications/${APP_NAME}.app"
SUPPORT_DIR="$HOME/Library/Application Support/Context"

echo ""
echo "  Installing ${APP_NAME} to Applications"
echo "  ────────────────────────────────────────"
echo ""

if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "✗  Xcode is required. Install Xcode, then run this again." >&2
  echo "   Or open DesktopApp/DesktopApp.xcodeproj and press ⌘B." >&2
  exit 1
fi

bash "$REPO/scripts/build_app.sh" Release

APP_SRC="$REPO/DesktopApp/build/DerivedData/Build/Products/Release/${APP_NAME}.app"
if [ ! -d "$APP_SRC" ]; then
  echo "✗  Build succeeded but ${APP_NAME}.app was not found." >&2
  exit 1
fi

echo ""
echo "▶  Copying to ${APP_DEST}"
if [ -d "$APP_DEST" ]; then
  rm -rf "$APP_DEST"
fi
cp -R "$APP_SRC" "$APP_DEST"
xattr -cr "$APP_DEST" 2>/dev/null || true

mkdir -p "$SUPPORT_DIR"
printf '%s\n' "$REPO" > "$SUPPORT_DIR/repo_path"

echo "▶  Registered backend at: $REPO"
echo ""
echo "  ✓  ${APP_NAME} is installed."
echo ""
echo "  Open it:"
echo "    • Applications folder → ${APP_NAME}"
echo "    • Spotlight → type \"Context\""
echo "    • Terminal → open -a Context"
echo ""
echo "  The app auto-starts the Python backend on launch."
echo "  Your data stays in ~/.kb/"
echo ""
