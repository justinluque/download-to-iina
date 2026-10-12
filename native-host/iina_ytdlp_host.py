#!/usr/bin/env python3
"""Native messaging host for the 'Download & Open in IINA (yt-dlp)' extension.

Firefox launches this script and talks to it over stdin/stdout using the
native messaging protocol (4-byte little-endian length prefix + JSON).
For each {"url": ...} message received, it downloads the media with yt-dlp
into ~/Downloads and then opens the resulting file in IINA.
"""

import json
import os
import shutil
import struct
import subprocess
import sys
import threading
from urllib.parse import urlsplit

DOWNLOAD_DIR = os.path.expanduser("~/Downloads")

# GUI-launched Firefox usually does NOT inherit the user's shell PATH, so
# `yt-dlp` on PATH inside a Terminal may still be invisible here. Fall back
# to common install locations.
CANDIDATE_YTDLP_PATHS = [
    "/opt/homebrew/bin/yt-dlp",
    "/usr/local/bin/yt-dlp",
    os.path.expanduser("~/.local/bin/yt-dlp"),
    os.path.expanduser("~/Library/Python/3.*/bin/yt-dlp"),
]


def find_yt_dlp():
    found = shutil.which("yt-dlp")
    if found:
        return found
    for candidate in CANDIDATE_YTDLP_PATHS:
        if "*" in candidate:
            import glob

            matches = glob.glob(candidate)
            if matches:
                return matches[0]
        elif os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        sys.exit(0)
    if len(raw_length) != 4:
        raise ValueError("Incomplete native message header.")
    length = struct.unpack("=I", raw_length)[0]
    if not 0 < length <= 1024 * 1024:
        raise ValueError("Invalid native message length.")
    raw_message = sys.stdin.buffer.read(length)
    if len(raw_message) != length:
        raise ValueError("Incomplete native message body.")
    message = json.loads(raw_message.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("Native message must be an object.")
    return message


_send_lock = threading.Lock()


def send_message(message_dict):
    encoded = json.dumps(message_dict).encode("utf-8")
    with _send_lock:
        sys.stdout.buffer.write(struct.pack("=I", len(encoded)))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()


def download_and_open(url):
    try:
        parsed = urlsplit(url) if isinstance(url, str) else None
        valid = parsed and parsed.scheme in ("http", "https") and parsed.hostname
    except ValueError:
        valid = False
    if not valid:
        send_message({"status": "error", "message": "Choose an HTTP or HTTPS media URL."})
        return

    yt_dlp = find_yt_dlp()
    if not yt_dlp:
        send_message({
            "status": "error",
            "message": "yt-dlp not found. Install it (e.g. `brew install yt-dlp`) "
                       "or edit CANDIDATE_YTDLP_PATHS in iina_ytdlp_host.py.",
        })
        return

    send_message({"status": "started"})

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    try:
        result = subprocess.run(
            [
                yt_dlp,
                "-o", os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
                "--no-simulate",
                "--print", "after_move:filepath",
                "--",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except Exception as exc:  # subprocess launch failure, timeout, etc.
        send_message({"status": "error", "message": str(exc)})
        return

    if result.returncode != 0:
        send_message({
            "status": "error",
            "message": (result.stderr or "yt-dlp failed").strip()[-2000:],
        })
        return

    lines = [line for line in result.stdout.strip().splitlines() if line]
    if not lines:
        send_message({"status": "error", "message": "yt-dlp did not report an output file."})
        return
    filepath = lines[-1]

    try:
        subprocess.run(["open", "-a", "IINA", filepath], check=True)
    except subprocess.CalledProcessError as exc:
        send_message({"status": "error", "message": f"Downloaded but failed to open in IINA: {exc}"})
        return

    send_message({"status": "done", "path": filepath})


def main():
    while True:
        try:
            message = read_message()
        except (ValueError, UnicodeError) as exc:
            send_message({"status": "error", "message": str(exc)})
            return
        url = message.get("url")
        if not url:
            send_message({"status": "error", "message": "No url in message."})
            continue
        # Run in a background thread so a slow download doesn't block us
        # from reading (and eventually responding to) further messages.
        threading.Thread(target=download_and_open, args=(url,), daemon=True).start()


if __name__ == "__main__":
    main()
