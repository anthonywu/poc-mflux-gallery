import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from starlette.testclient import TestClient

from mflux_gallery.config import AppConfig
from mflux_gallery.main import create_app


class FactoryTests(unittest.TestCase):
    def test_import_does_not_parse_arguments_or_change_cwd(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import os, sys
from pathlib import Path
sys.argv = ['unrelated-program', '--not-a-gallery-option']
cwd = Path.cwd()
before = set(cwd.iterdir())
import mflux_gallery.main
assert Path.cwd() == cwd
assert set(cwd.iterdir()) == before
""",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_apps_have_independent_roots_and_configuration(self):
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "first", root / "second"
            first.mkdir()
            second.mkdir()
            for name, folder in [("one.JPG", first), ("two.JPG", second)]:
                Image.new("RGB", (32, 16), "blue").save(folder / name)
            a = create_app(AppConfig(first, resize_max_width=16))
            b = create_app(AppConfig(second, resize_max_width=32))
            with TestClient(a) as ca, TestClient(b) as cb:
                self.assertIn("one.JPG", ca.get("/").text)
                self.assertNotIn("two.JPG", ca.get("/").text)
                self.assertIn("two.JPG", cb.get("/").text)
                self.assertEqual(
                    cb.get("/", follow_redirects=False).headers["location"],
                    "/?resize_width=32",
                )
                self.assertEqual(
                    ca.get("/one.JPG").content, (first / "one.JPG").read_bytes()
                )
                ca.post(
                    "/image_action",
                    data={"action": "delete", "gallery_path": "one.JPG"},
                )
                self.assertEqual(a.state.gallery.count_all_images(), 0)
                self.assertEqual(b.state.gallery.count_all_images(), 1)
            self.assertTrue((first / ".sesskey").is_file())
            self.assertTrue((second / ".sesskey").is_file())
        self.assertEqual(Path.cwd(), cwd)

    def test_invalid_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                AppConfig(Path(directory) / "missing")
            file = Path(directory) / "file"
            file.touch()
            with self.assertRaises(NotADirectoryError):
                AppConfig(file)

    def test_cli_configuration_survives_worker_import(self):
        from mflux_gallery import main

        with tempfile.TemporaryDirectory() as directory:

            def serve(**kwargs):
                self.assertTrue(kwargs["factory"])
                app = main._create_cli_app()
                self.assertEqual(app.state.config.load_limit, 7)
                self.assertEqual(app.state.config.directory, Path(directory))

            with (
                patch.object(
                    sys, "argv", ["mflux-gallery", directory, "--load-limit", "7"]
                ),
                patch.object(main, "serve", side_effect=serve),
            ):
                before = dict(os.environ)
                main.main()
                self.assertEqual(dict(os.environ), before)

    def test_debug_reload_with_relative_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gallery = root / "pictures"
            gallery.mkdir()
            Image.new("RGB", (32, 16), "blue").save(gallery / "sample.JPG")
            watched = gallery / "reload_probe.py"
            watched.write_text("# initial\n")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            with tempfile.TemporaryFile(mode="w+") as log:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "mflux_gallery.main",
                        "pictures",
                        "--debug",
                        "--port",
                        str(port),
                    ],
                    cwd=root,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
                try:
                    self.wait_for_server(process, log, port, starts=1)
                    watched.write_text("# changed to trigger reload\n")
                    self.wait_for_server(process, log, port, starts=2, watched=watched)
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/sample.JPG"
                    ) as response:
                        self.assertEqual(
                            response.read(), (gallery / "sample.JPG").read_bytes()
                        )
                finally:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=10)

    def wait_for_server(self, process, log, port, starts, watched=None):
        deadline = time.monotonic() + 20
        next_change = time.monotonic() + 1
        while time.monotonic() < deadline and process.poll() is None:
            # A worker can accept requests before the reload watcher is ready.
            if watched is not None and time.monotonic() >= next_change:
                watched.write_text(f"# reload probe {next_change}\n")
                next_change = time.monotonic() + 1
            log.seek(0)
            output = log.read()
            if len(re.findall("Started server process", output)) >= starts:
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/", timeout=1
                    ) as response:
                        if b"sample.JPG" in response.read():
                            return
                except OSError:  # noqa: PERF203 - wait for the worker to accept requests
                    pass
            time.sleep(0.1)
        log.seek(0)
        self.fail("Server did not become ready:\n" + log.read())
