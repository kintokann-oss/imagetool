"""Keeps a downscaled JPEG copy of each listing image (D14). Originals are never written to disk."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image


class ImageStore:
    def __init__(self, root: Path, max_size: int = 512) -> None:
        self._root = root
        self._max_size = max_size

    def save_thumbnail(self, listing_id: int, position: int, image: bytes) -> Path:
        folder = self._root / str(listing_id)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{position}.jpg"
        with Image.open(io.BytesIO(image)) as picture:
            copy = picture.convert("RGB")
            copy.thumbnail((self._max_size, self._max_size))
            copy.save(path, "JPEG", quality=85, optimize=True)
        return path
