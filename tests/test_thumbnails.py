import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from starlette.testclient import TestClient

from mflux_gallery.config import AppConfig
from mflux_gallery.main import create_app


class ThumbnailTests(unittest.TestCase):
    def test_dimensions_and_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with TestClient(create_app(AppConfig(root))) as client:
                for size in [(1000, 100), (100, 1000), (640, 640), (32, 16)]:
                    with self.subTest(size=size):
                        Image.new("RGB", size, "blue").save(root / "image.jpg")
                        response = client.get(
                            "/thumbnail", params={"gallery_path": "image.jpg"}
                        )
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.headers["content-type"], "image/webp")
                        with Image.open(io.BytesIO(response.content)) as image:
                            self.assertLessEqual(image.width, min(size[0], 128))
                            self.assertLessEqual(image.height, min(size[1], 96))
                            self.assertAlmostEqual(
                                image.width / image.height, size[0] / size[1], delta=0.2
                            )
                (root / "broken.jpg").write_text("not an image")
                for path in ["missing.jpg", "broken.jpg"]:
                    self.assertEqual(
                        client.get(
                            "/thumbnail", params={"gallery_path": path}
                        ).status_code,
                        404,
                    )
                self.assertEqual(
                    client.get(
                        "/thumbnail", params={"gallery_path": "../outside.jpg"}
                    ).status_code,
                    403,
                )
                with tempfile.TemporaryDirectory() as outside:
                    Image.new("RGB", (32, 32)).save(Path(outside) / "private.jpg")
                    (root / "link.jpg").symlink_to(Path(outside) / "private.jpg")
                    self.assertEqual(
                        client.get(
                            "/thumbnail", params={"gallery_path": "link.jpg"}
                        ).status_code,
                        403,
                    )
