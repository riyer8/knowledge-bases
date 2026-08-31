#!/bin/bash
# Build the Context macOS app with xcodebuild.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="$REPO/DesktopApp/DesktopApp.xcodeproj"
SCHEME="DesktopApp"
CONFIG="${1:-Debug}"
DERIVED="$REPO/DesktopApp/build"

echo "Building Context ($CONFIG)..."
xcodebuild \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -configuration "$CONFIG" \
  -derivedDataPath "$DERIVED/DerivedData" \
  build

APP="$DERIVED/DerivedData/Build/Products/$CONFIG/Context.app"
if [ -d "$APP" ]; then
  echo ""
  echo "Built: $APP"
  echo ""
  echo "Try it now:  open \"$APP\""
  echo "Install it:  bash scripts/install_app.sh"
else
  echo "Build finished but Context.app was not found at expected path." >&2
  exit 1
fi
