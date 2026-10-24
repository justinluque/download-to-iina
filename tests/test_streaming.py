"""Exercise native framing and process cancellation with a real child process."""
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import tempfile
import time
import unittest

HOST = Path(__file__).resolve().parents[1] / 'native-host/iina_ytdlp_host.py'


class StreamingTests(unittest.TestCase):
    def send(self, process, message):
        body = json.dumps(message).encode()
        process.stdin.write(struct.pack('=I', len(body)) + body)
        process.stdin.flush()

    def receive(self, process, timeout=5):
        deadline = time.monotonic() + timeout
        def read_exact(size):
            output = b''
            while len(output) < size:
                readable, _, _ = select.select([process.stdout], [], [], max(0, deadline-time.monotonic()))
                if not readable: self.fail('Timed out waiting for native message')
                chunk = os.read(process.stdout.fileno(), size-len(output))
                if not chunk: self.fail('Helper exited before sending expected message')
                output += chunk
            return output
        size = struct.unpack('=I', read_exact(4))[0]
        return json.loads(read_exact(size))

    def start(self, temporary, pause):
        root = Path(temporary)
        output = root / 'movie.mp4'
        output.write_bytes(b'test media')
        downloader = root / 'yt-dlp'
        downloader.write_text(f'''#!{sys.executable}
import json, time
print('IINA_EVENT:' + json.dumps({{"kind":"progress","downloaded":42,"total":100,"speed":10,"eta":6,"state":"downloading"}}), flush=True)
time.sleep({pause})
print('IINA_EVENT:' + json.dumps({{"kind":"file","path":{str(output)!r}}}), flush=True)
''')
        downloader.chmod(0o755)
        player = root / 'open'
        player.write_text(f'#!{sys.executable}\nfrom pathlib import Path\nPath({str(root / "opened")!r}).touch()\n')
        player.chmod(0o755)
        environment = {**os.environ, 'PATH': str(root)+os.pathsep+os.environ.get('PATH',''), 'HOME': str(root)}
        return subprocess.Popen([sys.executable, str(HOST)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, bufsize=0)

    def finish(self, process):
        process.stdin.close()
        try: process.wait(timeout=5)
        finally:
            if process.poll() is None: process.kill(); process.wait()
            error = process.stderr.read()
            process.stdout.close(); process.stderr.close()
        self.assertEqual(error, b'')

    def test_progress_arrives_before_download_finishes(self):
        with tempfile.TemporaryDirectory() as temporary:
            process = self.start(temporary, 0.5)
            try:
                self.send(process, {'id':'stream','url':'https://example.com/video'})
                self.assertEqual(self.receive(process)['status'], 'started')
                progress = self.receive(process)
                self.assertEqual(progress['percent'],42)
                self.assertFalse((Path(temporary)/'opened').exists())
                messages=[]
                while not messages or messages[-1]['status'] != 'done': messages.append(self.receive(process))
                self.assertTrue((Path(temporary)/'opened').exists())
                self.assertEqual(messages[-1]['id'],'stream')
            finally: self.finish(process)

    def test_cancellation_interrupts_child_and_prevents_playback(self):
        with tempfile.TemporaryDirectory() as temporary:
            process = self.start(temporary, 60)
            try:
                self.send(process, {'id':'cancel','url':'https://example.com/video'})
                self.receive(process)
                self.assertEqual(self.receive(process)['percent'],42)
                self.send(process, {'action':'cancel','id':'cancel'})
                self.assertEqual(self.receive(process, timeout=3)['status'],'cancelled')
                self.assertFalse((Path(temporary)/'opened').exists())
            finally: self.finish(process)

    def test_disconnect_stops_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            process = self.start(temporary, 60)
            self.send(process, {'id':'disconnect','url':'https://example.com/video'})
            self.receive(process); self.receive(process)
            self.finish(process)
            self.assertFalse((Path(temporary)/'opened').exists())
