"""Fixture engines: return the OCR text / image scores recorded in the mock fixtures.

They let the whole pipeline run (tests, dev, benchmark) without Tesseract or a GPU. The
benchmark with these engines measures the rules and dictionaries given realistic, noisy
OCR output — not the accuracy of the real models.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from imagetool.domain.models import Category, OcrResult


def _fixture_images(fixtures_dir: Path) -> dict[str, dict]:
    data = json.loads((fixtures_dir / "mock_marketplace" / "listings.json").read_text("utf-8"))
    return {
        f"mock://images/{image['file']}": image
        for listing in data["listings"]
        for image in listing.get("images", [])
    }


class FixtureOcrEngine:
    def __init__(self, fixtures_dir: Path) -> None:
        self._images = _fixture_images(fixtures_dir)

    def read(self, image: bytes, languages: list[str], image_url: str) -> OcrResult:
        text = self._images.get(image_url, {}).get("ocr_text", "")
        return OcrResult(text=text, lines=[line for line in text.splitlines() if line.strip()])


class FixtureImageClassifier:
    def __init__(self, fixtures_dir: Path) -> None:
        self._images = _fixture_images(fixtures_dir)

    def score(self, image: bytes, image_url: str) -> Mapping[Category, float]:
        scores = self._images.get(image_url, {}).get("image_scores", {})
        return {Category(category): float(score) for category, score in scores.items()}


class NullOcrEngine:
    def read(self, image: bytes, languages: list[str], image_url: str) -> OcrResult:
        return OcrResult(text="")


class NullImageClassifier:
    def score(self, image: bytes, image_url: str) -> Mapping[Category, float]:
        return {}
