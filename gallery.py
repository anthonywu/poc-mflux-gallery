import base64
import io
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
        load_limit=1000,
    ):
        self.gallery_dir = gallery_dir
        self.photo_suffixes = photo_suffixes
        self.resize_max_width = resize_max_width
        self.load_limit = load_limit

    def __iter__(self) -> Path:
        count = 0
        for suf in self.photo_suffixes:
            for _ in self.gallery_dir.rglob(f"*{suf}", case_sensitive=False):
                if count <= self.load_limit:
                    yield _
                count += 1

    async def get_image_as_base64(self, gallery_path, format="PNG"):
        with Image.open(self.gallery_dir / gallery_path) as img:
            original_width, original_height = img.size
            if self.resize_max_width and self.resize_max_width < original_width:
                resize_height = int(
                    (self.resize_max_width / original_width) * original_height
                )
                img = img.resize(
                    (self.resize_max_width, resize_height), Image.Resampling.LANCZOS
                )
            buffer = io.BytesIO()
            img.save(buffer, format=format)
            buffer.seek(0)
            img_bytes = buffer.read()
        base64_str = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/{format.lower()};base64,{base64_str}"

    async def delete_item(self, gallery_path: str | Path) -> tuple[Path, bool]:
        try:
            target = (self.gallery_dir / gallery_path).resolve()
            # safety: do not allow user to traverse above the gallery dir
            target.relative_to(self.gallery_dir)
        except ValueError as ve:
            raise InvalidPathValueError(f"cannot jailbreak to {target=}") from ve

        if target.exists():
            target.unlink()
            return target, True
        else:
            return target, False
