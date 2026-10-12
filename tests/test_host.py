import importlib.util
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "host", Path(__file__).resolve().parents[1] / "native-host/iina_ytdlp_host.py"
)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class NativeHostTests(unittest.TestCase):
    def read(self, payload):
        with patch.object(host.sys, "stdin", Mock(buffer=io.BytesIO(payload))):
            return host.read_message()

    def test_valid_message(self):
        body = json.dumps({"url": "https://example.com/video"}).encode()
        self.assertEqual(self.read(struct.pack("=I", len(body)) + body)["url"],
                         "https://example.com/video")

    def test_rejects_invalid_frames(self):
        for payload in (b"\x01", struct.pack("=I", 1048577),
                        struct.pack("=I", 10) + b"{}",
                        struct.pack("=I", 2) + b"[]",
                        struct.pack("=I", 1) + b"{"):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.read(payload)

    def test_rejects_non_web_urls_without_starting_process(self):
        for url in (None, 123, "--exec=evil", "file:///etc/passwd",
                    "https://", "https://[invalid", "javascript:alert(1)"):
            with self.subTest(url=url), patch.object(host, "send_message") as send, \
                    patch.object(host.subprocess, "run") as run:
                host.download_and_open(url)
                self.assertEqual(send.call_args.args[0]["status"], "error")
                run.assert_not_called()

    def test_download_then_open_and_report_success(self):
        download = Mock(returncode=0, stdout="/tmp/first.mp4\n/tmp/final.mp4\n")
        with patch.object(host, "find_yt_dlp", return_value="/opt/homebrew/bin/yt-dlp"), \
                patch.object(host.os, "makedirs"), \
                patch.object(host.subprocess, "run", side_effect=[download, Mock()]) as run, \
                patch.object(host, "send_message") as send:
            host.download_and_open("https://example.com/video")
            self.assertEqual(run.call_args_list[0].args[0][-2:],
                             ["--", "https://example.com/video"])
            self.assertEqual(run.call_args_list[1].args[0],
                             ["open", "-a", "IINA", "/tmp/final.mp4"])
            self.assertEqual(send.call_args.args[0],
                             {"status": "done", "path": "/tmp/final.mp4"})

    def test_download_failure_does_not_open_player(self):
        with patch.object(host, "find_yt_dlp", return_value="yt-dlp"), \
                patch.object(host.os, "makedirs"), \
                patch.object(host.subprocess, "run", return_value=Mock(returncode=1, stderr="failed")) as run, \
                patch.object(host, "send_message") as send:
            host.download_and_open("https://example.com/video")
            self.assertEqual(run.call_count, 1)
            self.assertEqual(send.call_args.args[0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
