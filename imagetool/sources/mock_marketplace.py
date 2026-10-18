"""Mock marketplace Source Adapter: serves fixture listings from disk (D9).

Image URLs look like `mock://images/y1.png`. A real adapter would make HTTP calls here;
nothing outside this module knows the fixture format.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from imagetool.domain.models import Listing, RunSpec
from imagetool.text.normalize import normalize

IMAGE_SCHEME = "mock://"


class MockMarketplaceAdapter:
    name = "mock_marketplace"

    def __init__(self, fixtures_dir: Path) -> None:
        self._root = fixtures_dir / "mock_marketplace"

    def raw_listings(self) -> list[dict[str, Any]]:
        return json.loads((self._root / "listings.json").read_text("utf-8"))["listings"]

    def fetch(self, spec: RunSpec) -> Iterator[Listing]:
        listings = [self._to_listing(raw) for raw in self.raw_listings()]
        listings.sort(key=lambda listing: listing.posted_at or date.min, reverse=True)
        yield from (listing for listing in listings if _matches(listing, spec))

    def fetch_image(self, url: str) -> bytes:
        if not url.startswith(IMAGE_SCHEME):
            raise ValueError(f"not a mock image url: {url}")
        relative = Path(url.removeprefix(IMAGE_SCHEME))
        path = (self._root / relative).resolve()
        if self._root.resolve() not in path.parents:
            raise ValueError(f"image path escapes fixtures: {url}")
        return path.read_bytes()

    def _to_listing(self, raw: dict[str, Any]) -> Listing:
        return Listing(
            source=self.name,
            source_listing_id=raw["id"],
            title=raw["title"],
            description=raw.get("description", ""),
            price=raw.get("price"),
            currency=raw.get("currency", "EUR"),
            country=raw.get("country"),
            posted_at=date.fromisoformat(raw["posted_at"]) if raw.get("posted_at") else None,
            source_url=raw.get("url", ""),
            image_urls=[f"{IMAGE_SCHEME}images/{image['file']}" for image in raw.get("images", [])],
            raw_attributes=raw.get("attributes", {}),
        )


def _matches(listing: Listing, spec: RunSpec) -> bool:
    if spec.query:
        haystack = normalize(f"{listing.title} {listing.description}")
        if not all(word in haystack for word in normalize(spec.query).split()):
            return False
    if spec.countries and listing.country not in spec.countries:
        return False
    if spec.price and listing.price is not None:
        if spec.price.min is not None and listing.price < spec.price.min:
            return False
        if spec.price.max is not None and listing.price > spec.price.max:
            return False
    if spec.posted_after and listing.posted_at and listing.posted_at < spec.posted_after:
        return False
    return True
