import asyncio
import base64
import io
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from PIL import Image

from mflux_gallery.gallery import Gallery


class CompatibilityTests(unittest.TestCase):
    def test_module_server_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            Image.new("RGB", (32, 16), "blue").save(Path(directory) / "sample.JPG")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            with tempfile.TemporaryFile(mode="w+") as log:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "mflux_gallery.main",
                        directory,
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                    ],
                    stdout=log,
                    stderr=log,
                )
                try:
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline and process.poll() is None:
                        try:
                            with urllib.request.urlopen(
                                f"http://127.0.0.1:{port}/", timeout=1
                            ) as response:
                                self.assertEqual(response.status, 200)
                                self.assertIn(b"sample.JPG", response.read())
                            return
                        except OSError:  # noqa: PERF203 - poll until the server is listening
                            time.sleep(0.1)
                    log.seek(0)
                    self.fail("Server failed to start:\n" + log.read())
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)

    def test_image_discovery_and_codecs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            image = Image.new("RGB", (64, 32), "red")
            for name, fmt in [
                ("sample.JPG", "JPEG"),
                ("sample.PNG", "PNG"),
                ("sample.HEIC", "HEIF"),
            ]:
                image.save(nested / name, format=fmt)
            (nested / "ignored.txt").write_text("not an image")
            gallery = Gallery(root, resize_max_width=16)
            self.assertEqual(gallery.count_all_images(), 3)
            paths = list(gallery)
            self.assertEqual(len(paths), 3)
            for path in paths:
                encoded = asyncio.run(gallery.get_image_as_base64(path))
                decoded = Image.open(
                    io.BytesIO(base64.b64decode(encoded.split(",", 1)[1]))
                )
                self.assertEqual(decoded.format, "WEBP")
                self.assertEqual(decoded.size, (16, 8))

    def test_gallery_routes(self):
        from starlette.testclient import TestClient

        from mflux_gallery.config import AppConfig
        from mflux_gallery.main import create_app

        with tempfile.TemporaryDirectory() as directory:
            Image.new("RGB", (32, 16), "blue").save(Path(directory) / "sample.JPG")
            with TestClient(create_app(AppConfig(Path(directory)))) as client:
                for path in ["/", "/oldest", "/shuffled"]:
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("sample.JPG", response.text)


if __name__ == "__main__":
    unittest.main()
