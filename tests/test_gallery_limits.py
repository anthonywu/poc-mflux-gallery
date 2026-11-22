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

    def test_pagination_slices_sorted_matches_into_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(5):
                path = root / f"{i:02}.jpg"
                path.touch()
                os.utime(path, (1000 + i,) * 2)
            app = create_app(AppConfig(root, load_limit=2))
            with TestClient(app) as client:
                page1 = client.get("/?resize_width=16", follow_redirects=False)
                self.assertEqual(page1.status_code, 200)
                self.assertIn("Page 1 of 3", page1.text)
                self.assertIn("1 / of batch size 2 / total: 5", page1.text)

                page2 = client.get("/?resize_width=16&page=2")
                self.assertIn("Page 2 of 3", page2.text)
                self.assertIn("3 / of batch size 2 / total: 5", page2.text)

                page3 = client.get("/?resize_width=16&page=3")
                cards = re.findall(r'id="container-image-', page3.text)
                self.assertEqual(len(cards), 1)
                self.assertIn("5 / of batch size 2 / total: 5", page3.text)

    def test_out_of_range_pages_redirect_to_the_last_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(3):
                (root / f"{i}.jpg").touch()
            with TestClient(create_app(AppConfig(root, load_limit=2))) as client:
                for page, clamped in [(0, 1), (-1, 1), (9, 2)]:
                    with self.subTest(page=page):
                        response = client.get(
                            f"/?resize_width=16&page={page}", follow_redirects=False
                        )
                        self.assertEqual(response.status_code, 307)
                        self.assertEqual(
                            response.headers["location"],
                            f"/?resize_width=16&page={clamped}",
                        )

    def test_shuffled_pages_are_stable_across_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(6):
                path = root / f"{i}.jpg"
                path.touch()
                os.utime(path, (1000 + i,) * 2)
            with TestClient(create_app(AppConfig(root, load_limit=3))) as client:
                page1 = client.get("/shuffled?resize_width=16").text
                page1_again = client.get("/shuffled?resize_width=16").text
                self.assertEqual(
                    re.findall(r'image-path-label">([^<]+)<', page1),
                    re.findall(r'image-path-label">([^<]+)<', page1_again),
                )
                # Pages do not repeat each other's images.
                page2 = client.get("/shuffled?resize_width=16&page=2").text
                self.assertEqual(
                    set(re.findall(r'image-path-label">([^<]+)<', page1))
                    & set(re.findall(r'image-path-label">([^<]+)<', page2)),
                    set(),
                )
