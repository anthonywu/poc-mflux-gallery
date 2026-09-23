import os
import re
import tempfile
import unittest
from pathlib import Path

from starlette.testclient import TestClient

from mflux_gallery.config import AppConfig
from mflux_gallery.gallery import Gallery
from mflux_gallery.main import create_app


class GalleryLimitTests(unittest.TestCase):
    def test_iterator_yields_exact_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["a.jpg", "b.PNG", "c.heic"]:
                (root / name).touch()
            for limit, expected in [(0, 0), (1, 1), (2, 2), (3, 3), (10, 3)]:
                with self.subTest(limit=limit):
                    gallery = Gallery(root, load_limit=limit)
                    self.assertEqual(len(list(gallery)), expected)
                    self.assertEqual(gallery.count_all_images(), 3)

    def test_negative_limit_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "non-negative"):
                Gallery(Path(directory), load_limit=-1)
            with self.assertRaisesRegex(ValueError, "non-negative"):
                AppConfig(Path(directory), load_limit=-1)

    def test_page_sorts_all_candidates_before_limiting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # These file paths are rendered lazily; no image decoding is needed.
            for i in range(1002):
                path = root / f"{i:04}.jpg"
                path.touch()
                os.utime(path, (1000 + i,) * 2)
            # A later suffix group proves discovery order cannot hide the newest image.
            newest = root / "newest.PNG"
            newest.touch()
            os.utime(newest, (9999,) * 2)
            app = create_app(AppConfig(root, load_limit=1))
            with TestClient(app) as client:
                latest = client.get("/?resize_width=16").text
                oldest = client.get("/oldest?resize_width=16").text
                self.assertIn("newest.PNG", latest)
                self.assertIn("0000.jpg", oldest)
                self.assertEqual(len(re.findall(r'id="container-image-', latest)), 1)
                self.assertIn("total: 1003", latest)
            with TestClient(create_app(AppConfig(root, load_limit=1002))) as client:
                html = client.get("/?resize_width=16").text
                self.assertEqual(len(re.findall(r'id="container-image-', html)), 1002)

    def test_zero_limit_renders_no_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.jpg").touch()
            with TestClient(create_app(AppConfig(root, load_limit=0))) as client:
                html = client.get("/?resize_width=16").text
                self.assertNotIn('id="container-image-', html)
                self.assertIn('id="photo-counter">1', html)
