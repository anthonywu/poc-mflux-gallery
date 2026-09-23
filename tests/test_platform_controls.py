import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from starlette.testclient import TestClient

from mflux_gallery import main
from mflux_gallery.config import AppConfig


class PlatformControlTests(unittest.TestCase):
    def test_finder_controls_and_endpoint_follow_server_capability(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (16, 16)).save(root / "image.jpg")
            for available in (False, True):
                with (
                    self.subTest(finder_available=available),
                    patch.object(main, "FINDER_AVAILABLE", available),
                    patch(
                        "mflux_gallery.gallery.subprocess.call", return_value=0
                    ) as reveal,
                    TestClient(main.create_app(AppConfig(root))) as client,
                ):
                    html = client.get("/?resize_width=512").text
                    self.assertEqual('value="show-in-finder"' in html, available)
                    self.assertEqual("<span>Show in Finder</span>" in html, available)
                    response = client.post(
                        "/image_action",
                        data={"action": "show-in-finder", "gallery_path": "image.jpg"},
                    )
                    self.assertEqual(response.status_code, 200 if available else 403)
                    if available:
                        reveal.assert_called_once_with(
                            ["/usr/bin/open", "-R", str(root / "image.jpg")]
                        )
                    else:
                        reveal.assert_not_called()
