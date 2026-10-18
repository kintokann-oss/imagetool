"""Classification core entry point: Listing + ImageEvidence → Classification. Pure, no I/O."""

from __future__ import annotations

from imagetool.classify.bundle import detect_bundle
from imagetool.classify.category import decide_category
from imagetool.classify.keywords import KeywordDictionary
from imagetool.classify.signals import image_signals, text_signals
from imagetool.domain.models import Classification, ImageEvidence, Listing, RunSpec
from imagetool.domain.ports import CardCatalog
from imagetool.identify import identify


def classify_listing(
    listing: Listing,
    images: list[ImageEvidence],
    spec: RunSpec,
    dictionary: KeywordDictionary,
    catalog: CardCatalog,
) -> Classification:
    signals = text_signals(listing, dictionary) + image_signals(images, dictionary)
    category, confidence = decide_category(signals, spec.categories, spec.min_confidence)
    is_bundle, item_count = detect_bundle(listing.title, listing.description)
    return Classification(
        category=category,
        confidence=confidence,
        is_bundle=is_bundle,
        estimated_item_count=item_count,
        identity=identify(category, listing, images, catalog),
        signals=signals,
    )
