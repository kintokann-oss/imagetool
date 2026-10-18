"""Turns a Listing and what the engines saw into Signals. Pure: no I/O."""

from __future__ import annotations

from collections import defaultdict

from imagetool.classify.keywords import KeywordDictionary, KeywordHit
from imagetool.domain.models import Category, ImageEvidence, Listing, Signal, SignalKind
from imagetool.identify.yugioh import SET_CODE_PATTERN

BASE_WEIGHTS = {
    SignalKind.TITLE_KEYWORD: 1.0,
    SignalKind.DESCRIPTION_KEYWORD: 0.5,
    SignalKind.OCR_KEYWORD: 0.8,
    SignalKind.SOURCE_CATEGORY: 0.7,
    SignalKind.PATTERN: 1.2,
    SignalKind.IMAGE_LABEL: 1.0,
}
# Repeated hits of the same kind for the same category count less and less.
DIMINISHING = (1.0, 0.5, 0.25)
MIN_IMAGE_SCORE = 0.5


def _keyword_signals(hits: list[KeywordHit], kind: SignalKind) -> list[Signal]:
    per_category: dict[Category, list[KeywordHit]] = defaultdict(list)
    for hit in hits:
        per_category[hit.category].append(hit)
    signals = []
    for category, category_hits in per_category.items():
        for factor, hit in zip(DIMINISHING, category_hits):
            signals.append(
                Signal(
                    kind=kind,
                    category=category,
                    weight=round(BASE_WEIGHTS[kind] * factor, 3),
                    detail=f"{hit.term} [{hit.language}]",
                )
            )
    return signals


def text_signals(listing: Listing, dictionary: KeywordDictionary) -> list[Signal]:
    signals = _keyword_signals(dictionary.find(listing.title), SignalKind.TITLE_KEYWORD)
    signals += _keyword_signals(dictionary.find(listing.description), SignalKind.DESCRIPTION_KEYWORD)
    source_category = listing.raw_attributes.get("category", "")
    if source_category:
        signals += _keyword_signals(dictionary.find(source_category), SignalKind.SOURCE_CATEGORY)[:1]
    return signals


def image_signals(images: list[ImageEvidence], dictionary: KeywordDictionary) -> list[Signal]:
    ocr_text = "\n".join(image.ocr.text for image in images)
    signals = _keyword_signals(dictionary.find(ocr_text), SignalKind.OCR_KEYWORD)

    set_codes = SET_CODE_PATTERN.findall(ocr_text)
    if set_codes:
        prefix, lang, number = set_codes[0]
        signals.append(
            Signal(
                kind=SignalKind.PATTERN,
                category=Category.YUGIOH_CARD,
                weight=BASE_WEIGHTS[SignalKind.PATTERN],
                detail=f"set code {prefix}-{lang}{number}",
            )
        )

    best: dict[Category, float] = {}
    for image in images:
        for category, score in image.category_scores.items():
            best[category] = max(best.get(category, 0.0), score)
    for category, score in best.items():
        if score >= MIN_IMAGE_SCORE and category != Category.UNKNOWN:
            signals.append(
                Signal(
                    kind=SignalKind.IMAGE_LABEL,
                    category=category,
                    weight=round(BASE_WEIGHTS[SignalKind.IMAGE_LABEL] * score, 3),
                    detail=f"image score {score:.2f}",
                )
            )
    return signals
