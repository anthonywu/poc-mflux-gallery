import base64
import io
import subprocess
import time
from collections.abc import Iterator
from itertools import islice
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


class InvalidPathValueError(ValueError):
    pass


class Gallery:
    DEFAULT_PHOTO_SUFFIXES = [".jpg", ".jpeg", ".png", ".heic"]

    def __init__(
        self,
        gallery_dir: Path,
        photo_suffixes: list[str] = DEFAULT_PHOTO_SUFFIXES,
        resize_max_width: int = 512,
        load_limit: int = 1000,
    ) -> None:
        if load_limit < 0:
            raise ValueError("load_limit must be non-negative")
        self.gallery_dir = gallery_dir
        self.photo_suffixes = photo_suffixes
        self.resize_max_width = resize_max_width
        self.load_limit = load_limit
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

    async def resolve_target(self, gallery_path: str | Path) -> Path:
        try:
            target = (self.gallery_dir / gallery_path).resolve()
            # safety: do not allow user to traverse above the gallery dir
            target.relative_to(self.gallery_dir)
            return target
        except ValueError as ve:
            raise InvalidPathValueError(f"cannot jailbreak to {target=}") from ve

    async def delete_item(
        self, gallery_path: str | Path, delete_other_suffixes: list[str] | None = None
    ) -> tuple[Path, bool]:
        target = await self.resolve_target(gallery_path)
        try:
            if not target.exists():
                return target, False
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
