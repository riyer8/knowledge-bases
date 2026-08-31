#!/bin/bash
# Register the Context native messaging host with Chrome (macOS).

set -e

REPO="$(cd "$(dirname "$0")/.." && pwd)"
HOST_SCRIPT="$REPO/chrome-extension/native-host/context_host.py"
EXT_ID="${1:-}"

if [ -z "$EXT_ID" ] && [ -f "$REPO/chrome-extension/.extension-id" ]; then
  EXT_ID="$(tr -d '[:space:]' < "$REPO/chrome-extension/.extension-id")"
fi

if [ -z "$EXT_ID" ]; then
  echo "Usage: bash chrome-extension/install-native-host.sh <extension-id>"
  echo ""
  echo "1. Open chrome://extensions"
  echo "2. Copy the ID under the Context extension"
  echo "3. Re-run: bash chrome-extension/install-native-host.sh YOUR_EXTENSION_ID"
  echo ""
  echo "Optional: save it once with:"
  echo "  echo YOUR_EXTENSION_ID > chrome-extension/.extension-id"
  exit 1
fi

chmod +x "$HOST_SCRIPT"
chmod +x "$REPO/scripts/start_backend.sh"

MANIFEST=$(cat <<EOF
{
  "name": "com.context.backend",
  "description": "Starts the Context Python backend",
  "path": "$HOST_SCRIPT",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://${EXT_ID}/"
  ]
}
EOF
)

TARGET_DIRS=(
  "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
  "$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
  "$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
  "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts"
)

for dir in "${TARGET_DIRS[@]}"; do
  mkdir -p "$dir"
  printf '%s\n' "$MANIFEST" > "$dir/com.context.backend.json"
  echo "Installed: $dir/com.context.backend.json"
done

echo ""
echo "Done. Reload the Context extension, then click it to auto-start the backend."
