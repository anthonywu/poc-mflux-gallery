"""Behavior guards captured before the maintainability refactor.

Only temporary paths and inline asset bodies are normalized in page fixtures.
Interaction attributes retain their pre-redesign hashes; visual snapshots include
the current inline asset hashes.
"""

import base64
import hashlib
import io
import json
import os
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from starlette.testclient import TestClient

from mflux_gallery import main
from mflux_gallery.cli import create_parser
from mflux_gallery.config import AppConfig

FIXTURES = Path(__file__).parent / "fixtures"
NOW = 1_700_000_000


class InteractionContract(HTMLParser):
    """Guard wiring independently of visual markup and inline asset changes."""

    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        # The copy control is new; retain the original wiring baseline.
        if "copy-filename" in dict(attrs).get("class", "").split():
            return
        behavior_attrs = {
            "id",
            "name",
            "type",
            "value",
            "onchange",
            "onclick",
            "open",
            "selected",
            "keyboard-enabled",
            "zoom",
            "speed",
        }
        kept = {
            key: value
            for key, value in attrs
            if key.startswith("hx-")
            or key in behavior_attrs
            or (key == "href" and value.startswith("/"))
        }
        if kept:
            self.items.append([tag, kept])


class GalleryRegressionTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory)
        self.main = main
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
        self.app = main.create_app(
            AppConfig(self.root, load_limit=2, resize_max_width=16)
        )
        self.client = self.enterContext(TestClient(self.app))
        self.enterContext(patch("time.time", return_value=NOW))

    def assert_snapshot(self, name, html):
        html = html.replace(str(self.root), "<GALLERY>")
        contract = InteractionContract()
        contract.feed(html)
        expected_contracts = json.loads(
            (FIXTURES / "interaction_contracts.json").read_text()
        )
        self.assertEqual(
            hashlib.sha256(
                json.dumps(contract.items, sort_keys=True).encode()
            ).hexdigest(),
            expected_contracts[name],
            "Interactive wiring changed from the pre-redesign baseline",
        )
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

    def test_zoom_preserves_original_resolution_and_restricts_paths(self):
        response = self.client.get("/image_zoom", params={"gallery_path": "new.JPG"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        with Image.open(io.BytesIO(response.content)) as image:
            self.assertEqual(image.size, (64, 32))
        for path, status in [("missing.JPG", 404), ("../outside.JPG", 403)]:
            response = self.client.get("/image_zoom", params={"gallery_path": path})
            self.assertEqual(response.status_code, status)

    def test_delete_sidecar_counter_and_htmx_event(self):
        self.assertEqual(self.app.state.gallery.count_all_images(), 3)
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
            self.assertEqual(self.app.state.gallery.count_all_images(), 2)

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
