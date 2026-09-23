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
        self.thumbnail_requests = []
        self.page.on(
            "request",
            lambda request: self.thumbnail_requests.append(request.url)
            if "/thumbnail?" in request.url
            else None,
        )
        self.image_requests = []
        self.page.on(
            "request",
            lambda request: self.image_requests.append(request.url)
            if "/image_element?" in request.url
            else None,
        )
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

    def test_filmstrip_is_optional_and_bounded(self):
        for i in range(5, 20):
            Image.new("RGB", (64, 64), "blue").save(self.root / f"image-{i}.jpg")
        self.page.reload()
        expect(self.page.locator(".swiper-slide-active img")).to_be_visible()
        self.assertEqual(self.thumbnail_requests, [])
        toggle = self.page.locator('[data-action="filmstrip"]')
        toggle.click()
        expect(self.page.locator("#filmstrip-items button")).to_have_count(9)
        self.page.wait_for_function(
            "document.querySelector('#filmstrip-items img')?.naturalWidth > 0"
        )
        self.assertLessEqual(len(self.thumbnail_requests), 9)
        self.page.locator("#filmstrip-items button").nth(3).click()
        expect(self.page.locator("#slide-position")).to_have_text("4 of 20")
        self.page.get_by_role("button", name="Next thumbnail group", exact=True).click()
        expect(self.page.locator("#slide-position")).to_have_text("13 of 20")
        expect(self.page.locator("#filmstrip-items button")).to_have_count(9)
        toggle.click()
        expect(self.page.locator("#filmstrip-items img")).to_have_count(0)
        expect(self.page.locator("#filmstrip")).to_be_hidden()
        self.assertEqual(self.errors, [])

    def test_loading_is_bounded_and_retry_recovers(self):
        expect(self.page.locator(".image-loader[data-loaded]")).to_have_count(2)
        self.assertEqual(len(self.image_requests), 2)
        for index in range(5):
            self.slide_to(index)
            expect(self.page.locator(".swiper-slide-active img")).to_be_visible()
            self.assertLessEqual(self.page.locator(".image-loader img").count(), 3)
        self.page.route(
            "**/image_element?*",
            lambda route: route.fulfill(status=503, body="Temporarily unavailable"),
            times=1,
        )
        self.page.reload()
        retry = self.page.locator('.swiper-slide-active [data-action="retry-image"]')
        expect(retry).to_be_visible()
        retry.click()
        expect(self.page.locator(".swiper-slide-active img")).to_be_visible()
        expect(retry).to_have_count(0)
        self.assertEqual(self.errors, [])

    def test_focus_metadata_and_prompt_copy(self):
        self.page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        self.page.keyboard.press("m")
        metadata = self.page.locator(".swiper-slide-active .metadata-section")
        expect(metadata).to_have_attribute("open", "")
        expect(metadata.locator(".metadata-values")).to_contain_text("Steps 20")
        metadata.locator(".copy-prompt").click()
        expect(metadata.locator(".copy-prompt")).to_have_text("Copied!")
        self.assertEqual(
            self.page.evaluate("navigator.clipboard.readText()"), "A <quiet> landscape"
        )
        self.page.locator('[data-action="focus"]').click()
        expect(self.page.locator("html")).to_have_class(re.compile("focus-mode"))
        expect(self.page.locator(".gallery-heading")).to_be_hidden()
        self.page.keyboard.press("n")
        expect(self.page.locator("#slide-position")).to_have_text("2 of 5")
        self.page.keyboard.press("Escape")
        expect(self.page.locator(".gallery-heading")).to_be_visible()
        expect(self.page.locator('[data-action="focus"]')).to_have_attribute(
            "aria-pressed", "false"
        )
        self.assertEqual(self.errors, [])

    def test_navigation_and_image_fit(self):
        expect(self.page.locator("#slide-position")).to_have_text("1 of 5")
        expect(
            self.page.get_by_role("button", name="Previous image", exact=True)
        ).to_be_disabled()
        self.page.get_by_role("button", name="Next image", exact=True).click()
        expect(self.page.locator("#slide-position")).to_have_text("2 of 5")
        self.page.keyboard.press("e")
        expect(self.page.locator("#slide-position")).to_have_text("5 of 5")
        expect(
            self.page.get_by_role("button", name="Next image", exact=True)
        ).to_be_disabled()
        for width in (1440, 640, 390, 280, 240):
            self.page.set_viewport_size({"width": width, "height": 900})
            image = self.page.locator(".swiper-slide-active img")
            expect(image).to_be_visible()
            box = image.bounding_box()
            self.assertAlmostEqual(box["width"], box["height"], delta=1)
            self.assertLessEqual(box["height"], 900)
            self.assertLessEqual(
                self.page.evaluate("document.documentElement.scrollWidth"), width
            )

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
