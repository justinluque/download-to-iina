#!/usr/bin/env python3
"""Firefox native host: stream yt-dlp progress, then open completed media in IINA."""
import collections
import glob
import json
import math
import os
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
CANDIDATE_YTDLP_PATHS = ["/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp",
    os.path.expanduser("~/.local/bin/yt-dlp"),
    os.path.expanduser("~/Library/Python/3.*/bin/yt-dlp")]
PREFIX = "IINA_EVENT:"
_send_lock = threading.Lock()
_jobs_lock = threading.Lock()
_jobs = {}


def find_yt_dlp():
    found = shutil.which("yt-dlp")
    if found:
        return found
    for candidate in CANDIDATE_YTDLP_PATHS:
        for path in sorted(glob.glob(candidate), reverse=True):
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
    return None



def find_ffmpeg():
    """Firefox launched from the Dock may not inherit Homebrew's PATH."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    for directory in ("/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")):
        path = os.path.join(directory, "ffmpeg")
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        raise EOFError
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


def send_message(message):
    encoded = json.dumps(message, allow_nan=False).encode("utf-8")
    with _send_lock:
        sys.stdout.buffer.write(struct.pack("=I", len(encoded)))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()


def stop_process(process):
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def number(value):
    return value if isinstance(value, (float, int)) and math.isfinite(value) and value >= 0 else None


def parse_event(line):
    if not line.startswith(PREFIX):
        return None
    try:
        event = json.loads(line[len(PREFIX):])
        if not isinstance(event, dict):
            return None
        return event
    except (ValueError, TypeError):
        return None


def download_and_open(url, request_id=None, cancel=None):
    cancel = cancel or threading.Event()
    def emit(status, **fields):
        message = {"status": status, **fields}
        if request_id is not None:
            message["id"] = request_id
        send_message(message)
    try:
        parsed = urlsplit(url) if isinstance(url, str) else None
        if not (parsed and parsed.scheme in ("http", "https") and parsed.hostname):
            raise ValueError("Choose an HTTP or HTTPS media URL.")
        yt_dlp = find_yt_dlp()
        if not yt_dlp:
            raise ValueError("yt-dlp was not found. Install it with brew install yt-dlp, then retry.")
        emit("started", phase="preparing")
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        progress = '{"kind":"progress","downloaded":%(progress.downloaded_bytes)j,"total":%(progress.total_bytes)j,"estimate":%(progress.total_bytes_estimate)j,"speed":%(progress.speed)j,"eta":%(progress.eta)j,"state":%(progress.status)j}'
        command = [yt_dlp, "--ignore-config", "--no-playlist", "--newline", "--progress",
            "--progress-delta", "0.3", "--output-na-placeholder", "null", "--no-colors", "--no-simulate",
            "-o", os.path.join(DOWNLOAD_DIR, "%(title)s [%(id)s].%(ext)s"),
            "--print", 'before_dl:' + PREFIX + '{"kind":"title","title":%(title)j}',
            "--print", 'after_move:' + PREFIX + '{"kind":"file","path":%(filepath)j}',
            "--progress-template", "download:" + PREFIX + progress,
            "--progress-template", 'postprocess:' + PREFIX + '{"kind":"processing"}',
            "--", url]
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            command[1:1] = ["--ffmpeg-location", os.path.dirname(ffmpeg)]
        else:
            # A combined stream can play directly without an external merger.
            command[1:1] = ["--format", "best"]
        timed_out = threading.Event()
        logs = collections.deque(maxlen=20)
        filepath = None
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace", start_new_session=True) as process:
            finished = threading.Event()
            def watch():
                deadline = time.monotonic() + 3600
                while not finished.wait(0.1):
                    if cancel.is_set() or time.monotonic() >= deadline:
                        if not cancel.is_set():
                            timed_out.set()
                        stop_process(process)
                        return
            watcher = threading.Thread(target=watch, daemon=True)
            watcher.start()
            try:
                for raw in process.stdout:
                    event = parse_event(raw.strip())
                    if not event:
                        logs.append(raw.strip()[-2000:])
                        continue
                    kind = event.get("kind")
                    if kind == "title" and isinstance(event.get("title"), str):
                        emit("progress", phase="preparing", title=event["title"][:500])
                    elif kind == "progress":
                        downloaded = number(event.get("downloaded"))
                        total = number(event.get("total")) or number(event.get("estimate"))
                        percent = min(100, 100 * downloaded / total) if downloaded is not None and total else None
                        emit("progress", phase="processing" if event.get("state") == "finished" else "downloading",
                             percent=percent, downloaded=downloaded, total=total,
                             speed=number(event.get("speed")), eta=number(event.get("eta")))
                    elif kind == "processing":
                        emit("progress", phase="processing", percent=None)
                    elif kind == "file" and isinstance(event.get("path"), str):
                        filepath = event["path"]
                code = process.wait()
                if timed_out.is_set():
                    raise ValueError("Download timed out after one hour. Try again.")
                if cancel.is_set():
                    emit("cancelled")
                    return
                if code:
                    raise ValueError("\n".join(logs)[-2000:] or "yt-dlp could not download this media.")
            finally:
                finished.set()
                stop_process(process)
                watcher.join(timeout=2)
        if not filepath or not os.path.isfile(filepath):
            raise ValueError("yt-dlp did not report a completed output file.")
        if cancel.is_set():
            emit("cancelled")
            return
        emit("progress", phase="opening", percent=100)
        try:
            subprocess.run(["open", "-a", "IINA", filepath], check=True, capture_output=True, timeout=15)
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError(f"Downloaded, but IINA could not open the file. Check that IINA is installed. File: {filepath}") from exc
        emit("done", path=filepath)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        emit("error", message=str(exc)[-2000:])


def run_job(url, request_id, cancel):
    try:
        download_and_open(url, request_id, cancel)
    finally:
        with _jobs_lock:
            _jobs.pop(request_id, None)


def main():
    try:
        while True:
            try:
                message = read_message()
            except EOFError:
                return
            except (ValueError, UnicodeError) as exc:
                send_message({"status": "error", "message": str(exc)})
                return
            request_id = message.get("id")
            if request_id is not None and (not isinstance(request_id, str) or len(request_id) > 100):
                send_message({"status": "error", "message": "Invalid request ID."})
                continue
            with _jobs_lock:
                if message.get("action") == "cancel":
                    if request_id in _jobs:
                        _jobs[request_id].set()
                    continue
                if request_id in _jobs or len(_jobs) >= 4:
                    send_message({"status": "error", "id": request_id, "message": "Helper is busy. Try again."})
                    continue
                cancel = threading.Event()
                _jobs[request_id] = cancel
            threading.Thread(target=run_job, args=(message.get("url"), request_id, cancel), daemon=True).start()
    finally:
        with _jobs_lock:
            for cancel in _jobs.values():
                cancel.set()
        # Allow cancellation watchdogs to reap child processes before the host exits.
        for thread in list(threading.enumerate()):
            if thread is not threading.current_thread():
                thread.join(timeout=2)


if __name__ == "__main__":
    main()
