"""Settings from environment variables (works the same on Windows and Linux)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURES = PACKAGE_ROOT / "fixtures"


@dataclass(frozen=True)
class Settings:
    database_path: Path
    data_dir: Path
    fixtures_dir: Path
    ocr_engine: str          # fixture | tesseract | none
    image_classifier: str    # fixture | clip | none
    tesseract_cmd: str | None
    clip_model: str
    thumbnail_size: int


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("IMAGETOOL_DATA_DIR", PACKAGE_ROOT / "data"))
    return Settings(
        database_path=Path(os.environ.get("IMAGETOOL_DATABASE", data_dir / "imagetool.db")),
        data_dir=data_dir,
        fixtures_dir=Path(os.environ.get("IMAGETOOL_FIXTURES_DIR", DEFAULT_FIXTURES)),
        ocr_engine=os.environ.get("IMAGETOOL_OCR", "fixture"),
        image_classifier=os.environ.get("IMAGETOOL_IMAGE_CLASSIFIER", "fixture"),
        tesseract_cmd=os.environ.get("IMAGETOOL_TESSERACT_CMD"),
        clip_model=os.environ.get("IMAGETOOL_CLIP_MODEL", "ViT-B-32/laion2b_s34b_b79k"),
        thumbnail_size=int(os.environ.get("IMAGETOOL_THUMBNAIL_SIZE", "512")),
    )
