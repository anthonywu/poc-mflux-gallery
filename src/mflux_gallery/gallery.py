import asyncio
import base64
import io
import subprocess
import time
import typing as t
from collections.abc import Iterator
from itertools import islice
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def thumbnail_bytes(path: Path) -> bytes:
    """Decode only on demand; constrain both dimensions of the response."""
    with Image.open(path) as image:
        image.thumbnail((128, 96), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=65)
        return buffer.getvalue()


class InvalidPathValueError(ValueError):
    pass


class Gallery:
    DEFAULT_PHOTO_SUFFIXES = [".jpg", ".jpeg", ".png", ".heic"]
    TRASH_DIR_NAME = ".mflux-trash"

    def __init__(
        self,
        gallery_dir: Path,
        photo_suffixes: list[str] = DEFAULT_PHOTO_SUFFIXES,
        resize_max_width: int = 512,
        load_limit: int = 1000,
        delete_mode: t.Literal["trash", "permanent"] = "permanent",
    ) -> None:
        if load_limit < 0:
            raise ValueError("load_limit must be non-negative")
        self.gallery_dir = gallery_dir
        self.photo_suffixes = photo_suffixes
        self.resize_max_width = resize_max_width
        self.load_limit = load_limit
        self.delete_mode = delete_mode
        self.trash_dir = gallery_dir / self.TRASH_DIR_NAME
        self._undo_stack: list[list[tuple[Path, Path]]] = []
        self._count_cache: int | None = None
        self._count_cache_time = 0
        self._cache_duration = 60  # Cache for 1 minute

    def __iter__(self) -> Iterator[Path]:
        return islice(self.iter_all_images(), self.load_limit)

    def iter_all_images(self) -> Iterator[Path]:
        """Discover all candidates so callers can sort before applying a limit."""
        for suffix in self.photo_suffixes:
            yield from self._paths_with_suffix(suffix)

    def _paths_with_suffix(self, suffix: str) -> Iterator[Path]:
        # Path.rglob(case_sensitive=...) requires Python 3.12.
        return (
            path
            for path in self.gallery_dir.rglob("*")
            if path.suffix.lower() == suffix.lower()
            and self.trash_dir not in path.parents
        )

    def count_all_images(self) -> int:
        """Count all images in the gallery without load limit. Results are cached for 1 minute."""
        current_time = time.monotonic()

        if (
            self._count_cache is not None
            and current_time - self._count_cache_time < self._cache_duration
        ):
            return self._count_cache

        total = 0
        print("Recounting images...")
        for suffix in self.photo_suffixes:
            total += sum(1 for _ in self._paths_with_suffix(suffix))

        self._count_cache = total
        self._count_cache_time = current_time

        return total

    def invalidate_count_cache(self) -> None:
        """Invalidate the count cache, forcing a recount on next access."""
        self._count_cache = None
        self._count_cache_time = 0

    async def get_image_as_base64(
        self,
        gallery_path: str | Path,
        format: str = "WEBP",
        resize_max_width: int | None = None,
    ) -> str:
        resize_width = (
            resize_max_width if resize_max_width is not None else self.resize_max_width
        )

        with Image.open(self.gallery_dir / gallery_path) as img:
            original_width, original_height = img.size
            if resize_width and resize_width < original_width:
                resize_height = int((resize_width / original_width) * original_height)
                img = img.resize(
                    (resize_width, resize_height), Image.Resampling.LANCZOS
                )
            buffer = io.BytesIO()
            img.save(buffer, format=format)
            img_bytes = buffer.getvalue()
        base64_str = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/{format.lower()};base64,{base64_str}"

    async def get_thumbnail(self, gallery_path: str) -> bytes:
        target = await self.resolve_target(gallery_path)
        return await asyncio.to_thread(thumbnail_bytes, target)

    async def resolve_target(self, gallery_path: str | Path) -> Path:
        try:
            target = (self.gallery_dir / gallery_path).resolve()
            # safety: do not allow user to traverse above the gallery dir
            target.relative_to(self.gallery_dir)
            return target
        except ValueError as ve:
            raise InvalidPathValueError(f"cannot jailbreak to {target=}") from ve

    def _trash_path(self, path: Path) -> Path:
        """Namespaced with a timestamp so repeated deletions never collide."""
        return self.trash_dir / f"{int(time.time() * 1000)}-{path.name}"

    def _trash(self, target: Path) -> Path:
        self.trash_dir.mkdir(exist_ok=True)
        trashed = self._trash_path(target)
        target.rename(trashed)
        return trashed

    async def delete_item(
        self, gallery_path: str | Path, delete_other_suffixes: list[str] | None = None
    ) -> tuple[Path, bool]:
        target = await self.resolve_target(gallery_path)
        try:
            if not target.exists():
                return target, False
            if self.delete_mode == "trash":
                moved: list[tuple[Path, Path]] = [(target, self._trash(target))]
                if delete_other_suffixes:
                    for suffix in delete_other_suffixes:
                        sidecar = target.with_suffix(suffix)
                        if sidecar.exists():
                            moved.append((sidecar, self._trash(sidecar)))
                self._undo_stack.append(moved)
                del self._undo_stack[:-20]  # Keep a bounded undo history.
                return target, True
            target.unlink()
            if delete_other_suffixes:
                for suffix in delete_other_suffixes:
                    target_suf = target.with_suffix(suffix)
                    if target_suf.exists():
                        target_suf.unlink()
            return target, True
        finally:
            # Missing files and partial failures can also make the cached count stale.
            self.invalidate_count_cache()

    def undo_last_delete(self) -> Path | None:
        """Restore the most recently trashed files; returns the image path or None."""
        while self._undo_stack:
            moved = self._undo_stack.pop()
            for original, trashed in moved:
                if trashed.exists():
                    original.parent.mkdir(parents=True, exist_ok=True)
                    trashed.rename(original)
            self.invalidate_count_cache()
            return moved[0][0]
        return None

    async def show_in_finder(
        self, gallery_path: str | Path
    ) -> tuple[Path, bool, int | str]:
        target = await self.resolve_target(gallery_path)
        try:
            return target, True, subprocess.call(["/usr/bin/open", "-R", str(target)])
        except subprocess.SubprocessError as e:
            return target, False, f"Failed to open Finder for {target}: {e}"
        except OSError as e:
            return target, False, f"OS error occurred trying to open {target}: {e}"
