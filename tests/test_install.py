import contextlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def test_installed_helper_runs_without_checkout_or_shell_path(self):
        installer = (ROOT / 'native-host/install.sh').read_text()
        program = installer.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        with tempfile.TemporaryDirectory(prefix="iina's setup ") as temporary:
            home = Path(temporary)
            with patch.object(Path, 'home', return_value=home), \
                    patch.object(sys, 'argv', ['install', str(ROOT / 'native-host')]), \
                    contextlib.redirect_stdout(io.StringIO()):
                exec(compile(program, 'installer', 'exec'), {})
            directory = home / 'Library/Application Support/Mozilla/NativeMessagingHosts'
            manifest = json.loads((directory / 'io.iina.ytdlp_host.json').read_text())
            self.assertEqual(manifest['allowed_extensions'], ['open_in_iina_ytdlp@iina.io'])
            payload = json.dumps({'url': 'file:///not-a-web-url'}).encode()
            result = subprocess.run([manifest['path']],
                input=struct.pack('=I', len(payload)) + payload,
                capture_output=True, check=True, env={'PATH': '/usr/bin:/bin'}, timeout=10)
            length = struct.unpack('=I', result.stdout[:4])[0]
            message = json.loads(result.stdout[4:4 + length])
            self.assertEqual(message['status'], 'error')
            self.assertIn('HTTP', message['message'])
            self.assertEqual(result.stderr, b'')
