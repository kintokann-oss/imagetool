"""Benchmark: run the pipeline over the mock fixtures and score against their expected results (D12)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from imagetool.classify import classify_listing
from imagetool.classify.keywords import KeywordDictionary
from imagetool.domain.models import ImageEvidence, RunSpec
from imagetool.domain.ports import CardCatalog, ImageClassifier, OcrEngine
from imagetool.sources.mock_marketplace import MockMarketplaceAdapter
from imagetool.text.language import detect_language, ocr_languages

PASS_BAR = 0.8


@dataclass
class BenchmarkReport:
    total: int = 0
    category_correct: int = 0
    card_total: int = 0
    card_correct: int = 0
    field_total: int = 0
    field_correct: int = 0
    misses: list[str] = field(default_factory=list)

    @property
    def category_accuracy(self) -> float:
        return self.category_correct / self.total if self.total else 0.0

    @property
    def card_accuracy(self) -> float:
        return self.card_correct / self.card_total if self.card_total else 0.0

    @property
    def field_accuracy(self) -> float:
        return self.field_correct / self.field_total if self.field_total else 0.0

    @property
    def passed(self) -> bool:
        return self.category_accuracy >= PASS_BAR and self.card_accuracy >= PASS_BAR

    def summary(self) -> str:
        lines = [
            f"category accuracy:        {self.category_accuracy:.0%} ({self.category_correct}/{self.total})",
            f"yugioh name + set:        {self.card_accuracy:.0%} ({self.card_correct}/{self.card_total})",
            f"identity + bundle fields: {self.field_accuracy:.0%} ({self.field_correct}/{self.field_total})",
            f"pass bar {PASS_BAR:.0%}:            {'PASS' if self.passed else 'FAIL'}",
        ]
        if self.misses:
            lines.append("misses:")
            lines += [f"  - {miss}" for miss in self.misses]
        return "\n".join(lines)


def run_benchmark(
    adapter: MockMarketplaceAdapter,
    ocr: OcrEngine,
    image_classifier: ImageClassifier,
    dictionary: KeywordDictionary,
    catalog: CardCatalog,
    min_confidence: float = 0.6,
) -> BenchmarkReport:
    report = BenchmarkReport()
    spec = RunSpec(max_listings=10_000, min_confidence=min_confidence)
    expected_by_id: dict[str, dict[str, Any]] = {raw["id"]: raw["expected"] for raw in adapter.raw_listings()}

    for listing in adapter.fetch(spec):
        expected = expected_by_id[listing.source_listing_id]
        language = detect_language(f"{listing.title}\n{listing.description}")
        images = []
        for url in listing.image_urls:
            image = adapter.fetch_image(url)
            images.append(
                ImageEvidence(
                    source_url=url,
                    ocr=ocr.read(image, ocr_languages(language), url),
                    category_scores=dict(image_classifier.score(image, url)),
                )
            )
        result = classify_listing(listing, images, spec, dictionary, catalog)
        got = result.identity.as_values()

        report.total += 1
        if result.category.value == expected["category"]:
            report.category_correct += 1
        else:
            report.misses.append(f"{listing.source_listing_id}: category {result.category.value} != {expected['category']}")

        expected_bundle = {"is_bundle": expected.get("is_bundle", False), "estimated_item_count": expected.get("estimated_item_count")}
        for name, value in expected_bundle.items():
            report.field_total += 1
            if getattr(result, name) == value:
                report.field_correct += 1
            else:
                report.misses.append(f"{listing.source_listing_id}: {name} {getattr(result, name)!r} != {value!r}")

        expected_identity: dict[str, str] = expected.get("identity", {})
        for name, value in expected_identity.items():
            report.field_total += 1
            if got.get(name) == value:
                report.field_correct += 1
            else:
                report.misses.append(f"{listing.source_listing_id}: {name} {got.get(name)!r} != {value!r}")

        if "card_name" in expected_identity:
            report.card_total += 1
            if all(got.get(name) == expected_identity.get(name) for name in ("card_name", "set_name")):
                report.card_correct += 1
    return report
