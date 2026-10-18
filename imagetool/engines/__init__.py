"""Engine selection from settings. Real engines are imported only when chosen."""

from __future__ import annotations

from imagetool.config import Settings
from imagetool.domain.ports import ImageClassifier, OcrEngine
from imagetool.engines.fixture import FixtureImageClassifier, FixtureOcrEngine, NullImageClassifier, NullOcrEngine


def build_ocr_engine(settings: Settings) -> OcrEngine:
    if settings.ocr_engine == "tesseract":
        from imagetool.engines.tesseract import TesseractOcrEngine

        return TesseractOcrEngine(settings.tesseract_cmd)
    if settings.ocr_engine == "fixture":
        return FixtureOcrEngine(settings.fixtures_dir)
    if settings.ocr_engine == "none":
        return NullOcrEngine()
    raise ValueError(f"unknown IMAGETOOL_OCR: {settings.ocr_engine}")


def build_image_classifier(settings: Settings) -> ImageClassifier:
    if settings.image_classifier == "clip":
        from imagetool.engines.clip import ClipImageClassifier

        return ClipImageClassifier(settings.clip_model)
    if settings.image_classifier == "fixture":
        return FixtureImageClassifier(settings.fixtures_dir)
    if settings.image_classifier == "none":
        return NullImageClassifier()
    raise ValueError(f"unknown IMAGETOOL_IMAGE_CLASSIFIER: {settings.image_classifier}")
