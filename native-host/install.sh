#!/bin/bash
# Installs the native messaging host manifest for Firefox on macOS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_SCRIPT="$SCRIPT_DIR/iina_ytdlp_host.py"
MANIFEST_DIR="$HOME/Library/Application Support/Mozilla/NativeMessagingHosts"
MANIFEST_PATH="$MANIFEST_DIR/io.iina.ytdlp_host.json"

chmod +x "$HOST_SCRIPT"

mkdir -p "$MANIFEST_DIR"
sed "s#__HOST_SCRIPT_PATH__#$HOST_SCRIPT#" "$SCRIPT_DIR/io.iina.ytdlp_host.json.template" > "$MANIFEST_PATH"

echo "Installed native messaging host manifest:"
echo "  $MANIFEST_PATH"
echo "Pointing at:"
echo "  $HOST_SCRIPT"
echo
echo "Now load the extension in Firefox: about:debugging -> This Firefox ->"
echo "Load Temporary Add-on -> select extension/manifest.json"
