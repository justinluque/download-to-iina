#!/bin/bash
# Install a standalone native messaging helper for Firefox on macOS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(command -v python3 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3 is required. Install it with: brew install python" >&2
  exit 1
fi

"$PYTHON_BIN" - "$SCRIPT_DIR" <<'PY'
import json
from pathlib import Path
import shlex
import shutil
import sys

source = Path(sys.argv[1])
manifest_dir = Path.home() / "Library/Application Support/Mozilla/NativeMessagingHosts"
host_dir = manifest_dir / "io.iina.ytdlp_host"
host_dir.mkdir(parents=True, exist_ok=True)
host_script = host_dir / "iina_ytdlp_host.py"
shutil.copy2(source / "iina_ytdlp_host.py", host_script)
launcher = host_dir / "launch.sh"
launcher.write_text(
    "#!/bin/sh\nexec " + shlex.quote(sys.executable) + " "
    + shlex.quote(str(host_script)) + "\n"
)
launcher.chmod(0o755)
manifest = json.loads((source / "io.iina.ytdlp_host.json.template").read_text())
manifest["path"] = str(launcher)
manifest_path = manifest_dir / "io.iina.ytdlp_host.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Installed native messaging helper: {manifest_path}")
print("Install the Firefox add-on:")
print("https://addons.mozilla.org/en-US/firefox/addon/download-to-iina/")
PY
