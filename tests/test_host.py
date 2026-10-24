import importlib.util
import io
import json
from pathlib import Path
import struct
import threading
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location("host", Path(__file__).resolve().parents[1] / "native-host/iina_ytdlp_host.py")
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class NativeHostTests(unittest.TestCase):
    def read(self, payload):
        with patch.object(host.sys, "stdin", Mock(buffer=io.BytesIO(payload))):
            return host.read_message()

    def test_valid_message(self):
        body = json.dumps({"url": "https://example.com/video"}).encode()
        self.assertEqual(self.read(struct.pack("=I", len(body)) + body)["url"], "https://example.com/video")

    def test_rejects_invalid_frames(self):
        for payload in (b"\x01", struct.pack("=I", 1048577), struct.pack("=I", 10) + b"{}", struct.pack("=I", 2) + b"[]", struct.pack("=I", 1) + b"{"):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.read(payload)

    def test_clean_eof(self):
        with self.assertRaises(EOFError): self.read(b"")

    def test_rejects_non_web_urls_without_starting_process(self):
        for url in (None, 123, "--exec=evil", "file:///etc/passwd", "https://", "https://[invalid", "javascript:alert(1)"):
            with self.subTest(url=url), patch.object(host, "send_message") as send, patch.object(host.subprocess, "Popen") as launch:
                host.download_and_open(url)
                self.assertEqual(send.call_args.args[0]["status"], "error")
                launch.assert_not_called()

    def run_download(self, events, code=0, cancel=None, open_error=None, exists=True):
        lines = [host.PREFIX + json.dumps(event) + "\n" if isinstance(event, dict) else event + "\n" for event in events]
        process = Mock(stdout=iter(lines))
        process.wait.return_value = code
        process.poll.return_value = code
        process.__enter__ = Mock(return_value=process)
        process.__exit__ = Mock(return_value=False)
        with patch.object(host, "find_yt_dlp", return_value="yt-dlp"), patch.object(host.os, "makedirs"), \
                patch.object(host.os.path, "isfile", return_value=exists), \
                patch.object(host.subprocess, "Popen", return_value=process) as launch, \
                patch.object(host.subprocess, "run", side_effect=open_error) as player, \
                patch.object(host, "send_message") as send:
            host.download_and_open("https://example.com/video", "job-1", cancel)
            return [call.args[0] for call in send.call_args_list], launch.call_args.args[0], player

    def test_finds_homebrew_ffmpeg_without_shell_path(self):
        with patch.object(host.shutil, "which", return_value=None), \
                patch.object(host.os.path, "isfile", side_effect=lambda path: path == "/opt/homebrew/bin/ffmpeg"), \
                patch.object(host.os, "access", return_value=True):
            self.assertEqual(host.find_ffmpeg(), "/opt/homebrew/bin/ffmpeg")

    def test_passes_ffmpeg_location_to_downloader(self):
        with patch.object(host, "find_ffmpeg", return_value="/opt/homebrew/bin/ffmpeg"):
            _, command, _ = self.run_download([{"kind": "file", "path": "/tmp/a"}])
            self.assertEqual(command[command.index("--ffmpeg-location") + 1], "/opt/homebrew/bin")

    def test_uses_combined_media_when_ffmpeg_is_unavailable(self):
        with patch.object(host, "find_ffmpeg", return_value=None):
            _, command, _ = self.run_download([{"kind": "file", "path": "/tmp/a"}])
            self.assertEqual(command[command.index("--format") + 1], "best")

    def test_stream_progress_then_open_completed_file(self):
        messages, command, player = self.run_download([
            {"kind": "title", "title": 'A "title"'},
            {"kind": "progress", "downloaded": 25, "total": 100, "speed": 5, "eta": 15, "state": "downloading"},
            {"kind": "processing"}, {"kind": "file", "path": "/tmp/finished.mp4"}])
        self.assertEqual(command[-2:], ["--", "https://example.com/video"])
        self.assertIn("--no-playlist", command)
        self.assertEqual(command[command.index("--output-na-placeholder") + 1], "null")
        self.assertTrue(all(message["id"] == "job-1" for message in messages))
        self.assertEqual(messages[2]["percent"], 25)
        self.assertEqual(messages[2]["speed"], 5)
        self.assertEqual(messages[2]["eta"], 15)
        self.assertEqual(messages[3]["phase"], "processing")
        self.assertEqual(messages[-1], {"status": "done", "id": "job-1", "path": "/tmp/finished.mp4"})
        self.assertEqual(player.call_args.args[0], ["open", "-a", "IINA", "/tmp/finished.mp4"])

    def test_unknown_sizes_and_nonfinite_numbers(self):
        messages, _, _ = self.run_download([{"kind": "progress", "downloaded": 1, "total": "NA", "speed": float("nan"), "eta": -1}, {"kind": "file", "path": "/tmp/a"}])
        self.assertIsNone(messages[1]["percent"])
        self.assertIsNone(messages[1]["speed"])
        self.assertIsNone(messages[1]["eta"])
        json.dumps(messages, allow_nan=False)

    def test_failure_does_not_open_iina(self):
        messages, _, player = self.run_download(["ERROR: unavailable"], code=1)
        player.assert_not_called()
        self.assertEqual(messages[-1]["message"], "ERROR: unavailable")

    def test_missing_output_does_not_open_iina(self):
        for events, exists in (([], True), ([{"kind": "file", "path": "/missing"}], False)):
            messages, _, player = self.run_download(events, exists=exists)
            player.assert_not_called()
            self.assertEqual(messages[-1]["status"], "error")

    def test_cancelled_download_never_opens_iina(self):
        cancel = threading.Event(); cancel.set()
        messages, _, player = self.run_download([{"kind": "file", "path": "/tmp/a"}], cancel=cancel)
        player.assert_not_called()
        self.assertEqual(messages[-1]["status"], "cancelled")

    def test_player_failure_keeps_download_location(self):
        messages, _, _ = self.run_download([{"kind": "file", "path": "/tmp/a"}], open_error=OSError("No IINA"))
        self.assertEqual(messages[-1]["status"], "error")
        self.assertIn("/tmp/a", messages[-1]["message"])

    def test_ignores_malformed_events(self):
        for text in ("plain", host.PREFIX + "{", host.PREFIX + "[]"):
            self.assertIsNone(host.parse_event(text))


if __name__ == "__main__": unittest.main()
