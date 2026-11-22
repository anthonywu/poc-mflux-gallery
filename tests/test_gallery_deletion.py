import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mflux_gallery.gallery import Gallery


class GalleryDeletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
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

    async def test_trash_mode_keeps_files_hidden_from_the_gallery(self):
        self.gallery.delete_mode = "trash"
        for name in ["photo.jpg", "photo.json", "keep.jpg"]:
            self.add_file(name)
        self.assertEqual(self.gallery.count_all_images(), 2)
        _, deleted = await self.gallery.delete_item("photo.jpg", [".json"])
        self.assertTrue(deleted)
        self.assertFalse((self.root / "photo.jpg").exists())
        self.assertFalse((self.root / "photo.json").exists())
        self.assertTrue((self.root / "keep.jpg").exists())
        trashed = list((self.root / Gallery.TRASH_DIR_NAME).iterdir())
        self.assertEqual(
            {p.name.split("-", 1)[1] for p in trashed}, {"photo.jpg", "photo.json"}
        )
        # Trashed images are neither counted nor iterated.
        self.assertEqual(self.gallery.count_all_images(), 1)
        self.assertEqual(len(list(self.gallery.iter_all_images())), 1)

    async def test_undo_restores_file_and_sidecar(self):
        self.gallery.delete_mode = "trash"
        self.add_file("photo.jpg")
        self.add_file("photo.json")
        await self.gallery.delete_item("photo.jpg", [".json"])
        self.assertEqual(self.gallery.count_all_images(), 0)
        restored = self.gallery.undo_last_delete()
        self.assertEqual(restored, self.root / "photo.jpg")
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertTrue((self.root / "photo.json").exists())
        self.assertEqual(self.gallery.count_all_images(), 1)

    async def test_undo_without_deletions_returns_none(self):
        self.assertIsNone(self.gallery.undo_last_delete())

    async def test_undo_restores_most_recent_deletion_first(self):
        self.gallery.delete_mode = "trash"
        self.add_file("first.jpg")
        self.add_file("second.jpg")
        await self.gallery.delete_item("first.jpg")
        await self.gallery.delete_item("second.jpg")
        restored = self.gallery.undo_last_delete()
        self.assertEqual(restored, self.root / "second.jpg")
        restored = self.gallery.undo_last_delete()
        self.assertEqual(restored, self.root / "first.jpg")

    async def test_permanent_mode_cannot_be_undone(self):
        self.gallery.delete_mode = "permanent"
        self.add_file("photo.jpg")
        await self.gallery.delete_item("photo.jpg")
        self.assertIsNone(self.gallery.undo_last_delete())
