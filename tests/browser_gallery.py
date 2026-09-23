"""Opt-in browser regressions: uv run --with playwright python tests/browser_gallery.py.

Uses only generated temporary images. Set GALLERY_BROWSER to a Chromium executable,
or install Playwright's Chromium with `uv run --with playwright playwright install chromium`.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

from PIL import Image
from playwright.sync_api import expect, sync_playwright


class GalleryBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp)
        for i in range(5):
            path = self.root / f"image-{i}.jpg"
            Image.new("RGB", (640, 640), (40 * i, 80, 120)).save(path)
            path.with_suffix(".json").write_text(
                json.dumps(
                    {"prompt": "A <quiet> landscape", "steps": 20, "guidance": 3.5}
                )
            )
            os.utime(path, (1000 + i,) * 2)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        code = "from pathlib import Path; import sys, uvicorn; from mflux_gallery.main import create_app; from mflux_gallery.config import AppConfig; uvicorn.run(create_app(AppConfig(Path(sys.argv[1]))), host='127.0.0.1', port=int(sys.argv[2]))"
        server = subprocess.Popen(
            [sys.executable, "-c", code, self.temp, str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(self.stop_server, server)
        for _ in range(100):
            try:
                with urlopen(self.url, timeout=1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            self.fail("Preview server did not start")
        playwright = self.enterContext(sync_playwright())
        executable = os.environ.get("GALLERY_BROWSER") or shutil.which("chromium")
        self.browser = playwright.chromium.launch(
            executable_path=executable, headless=True, args=["--no-sandbox"]
        )
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.url + "/?resize_width=512")
        self.page.wait_for_selector(".swiper-slide-active img")

    @staticmethod
    def stop_server(server):
        server.terminate()
        server.wait(timeout=10)

    def slide_to(self, index):
        self.page.locator("swiper-container").evaluate(
            "(el, i) => el.swiper.slideTo(i, 0)", index
        )
        self.page.wait_for_timeout(100)

    def test_delete_removes_only_requested_slide(self):
        for index, remaining in [(2, 4), (0, 3), (2, 2), (1, 1), (0, 0)]:
            self.slide_to(index)
            slide = self.page.locator(".swiper-slide-active")
            filename = slide.locator(".copy-filename").get_attribute("data-filename")
            slide.locator(".delete-image").click()
            expect(self.page.locator("swiper-slide")).to_have_count(remaining)
            expect(self.page.locator("#photo-counter")).to_have_text(str(remaining))
            self.assertFalse((self.root / filename).exists())
            self.assertEqual(len(list(self.root.glob("*.jpg"))), remaining)
        self.assertEqual(self.errors, [])

    def test_delete_during_navigation_keeps_the_new_active_image(self):
        pending = []
        self.page.route("**/image_action", lambda route: pending.append(route))
        self.page.locator(".swiper-slide-active .delete-image").click()
        self.slide_to(2)
        active = self.page.locator(".swiper-slide-active .copy-filename").get_attribute(
            "data-filename"
        )
        self.assertEqual(len(pending), 1)
        pending[0].fulfill(response=pending[0].fetch())
        expect(self.page.locator("swiper-slide")).to_have_count(4)
        expect(
            self.page.locator(".swiper-slide-active .copy-filename")
        ).to_have_attribute("data-filename", active)
        self.assertTrue((self.root / active).exists())

    def test_delete_failure_restores_slide(self):
        self.page.route(
            "**/image_action",
            lambda route: route.fulfill(status=500, body="Deletion failed"),
        )
        self.page.locator(".swiper-slide-active .delete-image").click()
        expect(self.page.locator("swiper-slide")).to_have_count(5)
        expect(self.page.locator(".swiper-slide-active")).not_to_have_class(
            re.compile("deleting")
        )
        expect(self.page.locator(".swiper-slide-active .delete-image")).to_be_enabled()
        self.assertEqual(len(list(self.root.glob("*.jpg"))), 5)


if __name__ == "__main__":
    unittest.main()
