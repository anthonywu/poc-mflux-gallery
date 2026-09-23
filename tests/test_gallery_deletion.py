import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mflux_gallery.gallery import Gallery


class GalleryDeletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.gallery = Gallery(self.root)

    def add_file(self, name):
        path = self.root / name
        path.touch()
        return path

    async def test_deleting_non_image_does_not_decrement_image_count(self):
        self.add_file("photo.jpg")
        self.add_file("notes.json")
        self.assertEqual(self.gallery.count_all_images(), 1)
        _, deleted = await self.gallery.delete_item("notes.json")
        self.assertTrue(deleted)
        self.assertEqual(self.gallery.count_all_images(), 1)

    async def test_deleting_image_sidecars_recounts_all_removed_images(self):
        for name in ["photo.jpg", "photo.png", "photo.json", "keep.jpg"]:
            self.add_file(name)
        self.assertEqual(self.gallery.count_all_images(), 3)
        _, deleted = await self.gallery.delete_item("photo.jpg", [".png", ".json"])
        self.assertTrue(deleted)
        self.assertEqual(self.gallery.count_all_images(), 1)
        self.assertEqual({p.name for p in self.root.iterdir()}, {"keep.jpg"})

    async def test_missing_image_invalidates_previously_cached_count(self):
        path = self.add_file("photo.jpg")
        self.assertEqual(self.gallery.count_all_images(), 1)
        path.unlink()  # Another process removed the image before the request.
        _, deleted = await self.gallery.delete_item("photo.jpg")
        self.assertFalse(deleted)
        self.assertEqual(self.gallery.count_all_images(), 0)

    async def test_partial_deletion_invalidates_cache_even_on_error(self):
        for name in ["photo.jpg", "photo.json", "keep.jpg"]:
            self.add_file(name)
        self.assertEqual(self.gallery.count_all_images(), 2)
        unlink = Path.unlink

        def fail_on_sidecar(path, *args, **kwargs):
            if path.suffix == ".json":
                raise PermissionError("sidecar is read-only")
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail_on_sidecar):
            with self.assertRaises(PermissionError):
                await self.gallery.delete_item("photo.jpg", [".json"])
        self.assertFalse((self.root / "photo.jpg").exists())
        self.assertTrue((self.root / "photo.json").exists())
        self.assertEqual(self.gallery.count_all_images(), 1)

    async def test_deleting_new_image_does_not_make_cached_count_negative(self):
        self.assertEqual(self.gallery.count_all_images(), 0)
        self.add_file("new.jpg")
        await self.gallery.delete_item("new.jpg")
        self.assertEqual(self.gallery.count_all_images(), 0)

    async def test_deletion_refreshes_count_after_external_addition(self):
        self.add_file("old.jpg")
        self.assertEqual(self.gallery.count_all_images(), 1)
        self.add_file("new.jpg")
        await self.gallery.delete_item("old.jpg")
        self.assertEqual(self.gallery.count_all_images(), 1)
