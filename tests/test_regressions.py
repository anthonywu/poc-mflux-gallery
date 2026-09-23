"""Behavior guards captured before the maintainability refactor.

Only temporary paths and inline asset bodies are normalized in page fixtures.
The asset bodies are checked separately using their pre-refactor SHA-256 hashes.
"""

import base64
import hashlib
import importlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from starlette.testclient import TestClient

from mflux_gallery.cli import create_parser

FIXTURES = Path(__file__).parent / "fixtures"
NOW = 1_700_000_000


class GalleryRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        cwd = Path.cwd()
        try:
            with patch.object(
                sys,
                "argv",
                [
                    "mflux-gallery",
                    str(cls.root),
                    "--load-limit",
                    "2",
                    "--resize-max-width",
                    "16",
                ],
            ):
                cls.main = importlib.import_module("mflux_gallery.main")
        finally:
            os.chdir(cwd)

    def setUp(self):
        for path in self.root.iterdir():
            path.unlink()
        for index, name in enumerate(["old.JPG", "middle.JPG", "new.JPG"]):
            path = self.root / name
            Image.new("RGB", (64, 32), "blue").save(path)
            os.utime(path, (NOW - 180 + index * 60,) * 2)
        (self.root / "new.json").write_text(
            json.dumps(
                {
                    "prompt": "a <blue> bird & clouds",
                    "guidance": 3.5,
                    "steps": 4,
                }
            )
        )
        self.main.app_gallery.invalidate_count_cache()
        self.client = self.enterContext(TestClient(self.main.app))
        self.enterContext(patch("time.time", return_value=NOW))

    def assert_snapshot(self, name, html):
        html = html.replace(str(self.root), "<GALLERY>")
        # Keep exact asset content guarded without duplicating it in every fixture.
        for tag in ("script", "style"):
            html = re.sub(
                rf"(<{tag}[^>]*>)(.*?)(</{tag}>)",
                lambda m: m[1]
                + (
                    "sha256:" + hashlib.sha256(m[2].encode()).hexdigest()
                    if m[2]
                    else ""
                )
                + m[3],
                html,
                flags=re.S,
            )
        expected = (FIXTURES / name).read_text()
        self.assertEqual(html, expected)

    def test_page_rendering_redirects_order_and_limit(self):
        for route, fixture in [
            ("/", "latest.html"),
            ("/oldest", "oldest.html"),
            ("/shuffled", "shuffled.html"),
        ]:
            with self.subTest(route=route):
                redirect = self.client.get(route, follow_redirects=False)
                self.assertEqual(redirect.status_code, 307)
                self.assertEqual(
                    redirect.headers["location"], route + "?resize_width=16"
                )
                # Fix the shuffle outcome without relying on the RNG implementation.
                with patch.object(
                    self.main.random, "shuffle", side_effect=lambda xs: xs.reverse()
                ):
                    response = self.client.get(route + "?resize_width=32")
                self.assertEqual(response.status_code, 200)
                self.assert_snapshot(fixture, response.text)

    def test_lazy_image_metadata_and_resize(self):
        response = self.client.get(
            "/image_element",
            params={
                "gallery_path": "new.JPG",
                "resize_width": 8,
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(response.status_code, 200)
        payload = re.search(r'data:image/webp;base64,([^"\s]+)', response.text)[1]
        with Image.open(io.BytesIO(base64.b64decode(payload))) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (8, 4))
        self.assert_snapshot("image.html", response.text.replace(payload, "<IMAGE>"))

    def test_missing_and_invalid_metadata(self):
        for content in [None, "{broken json"]:
            with self.subTest(content=content):
                path = self.root / "old.json"
                if content is not None:
                    path.write_text(content)
                response = self.client.get(
                    "/image_element?gallery_path=old.JPG",
                    headers={"HX-Request": "true"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("metadata-section", response.text)
                payload = re.search(r'data:image/webp;base64,([^"\s]+)', response.text)[
                    1
                ]
                with Image.open(io.BytesIO(base64.b64decode(payload))) as image:
                    self.assertEqual(image.size, (16, 8))
        response = self.client.get(
            "/image_element?gallery_path=missing.JPG", headers={"HX-Request": "true"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("missing.JPG is invalid path", response.text)

    def test_delete_sidecar_counter_and_htmx_event(self):
        self.assertEqual(self.main.app_gallery.count_all_images(), 3)
        for _ in range(2):  # Repeated deletion keeps the current missing-file behavior.
            response = self.client.post(
                "/image_action",
                data={
                    "action": " DELETE ",
                    "gallery_path": "new.JPG",
                },
                headers={"HX-Request": "true"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["hx-trigger"], "delete-successful")
            self.assert_snapshot("delete.html", response.text)
            self.assertFalse((self.root / "new.JPG").exists())
            self.assertFalse((self.root / "new.json").exists())
            self.assertEqual(self.main.app_gallery.count_all_images(), 2)

    def test_action_errors_and_finder_notifications(self):
        for action, path in [("unknown", "new.JPG"), ("delete", "../outside.JPG")]:
            response = self.client.post(
                "/image_action",
                data={
                    "action": action,
                    "gallery_path": path,
                },
            )
            self.assertEqual(response.status_code, 403)
        for result, status, message in [
            (0, 200, "Opened"),
            (OSError("Finder unavailable"), 500, "OS error"),
        ]:
            with (
                self.subTest(status=status),
                patch(
                    "mflux_gallery.gallery.subprocess.call",
                    **(
                        {"side_effect": result}
                        if isinstance(result, Exception)
                        else {"return_value": result}
                    ),
                ) as finder,
            ):
                response = self.client.post(
                    "/image_action",
                    data={
                        "action": "show-in-finder",
                        "gallery_path": "new.JPG",
                    },
                )
                self.assertEqual(response.status_code, status)
                self.assertIn(message, response.text)
                finder.assert_called_once_with(
                    ["/usr/bin/open", "-R", str(self.root / "new.JPG")]
                )
                page = self.client.get("/?resize_width=16")
                self.assertIn(message, page.text)

    def test_empty_gallery(self):
        for path in self.root.iterdir():
            path.unlink()
        response = self.client.get("/?resize_width=16")
        self.assertEqual(response.status_code, 200)
        self.assert_snapshot("empty.html", response.text)

    def test_cli_defaults(self):
        args = create_parser().parse_args([str(self.root)])
        self.assertEqual(
            vars(args),
            {
                "directory": self.root,
                "host": "127.0.0.1",
                "port": 9000,
                "delete_mode": "permanent",
                "load_limit": 100,
                "debug": False,
                "resize_max_width": 512,
            },
        )
