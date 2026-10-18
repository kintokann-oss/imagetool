"""Ports: the only ways the classification core talks to the outside world."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol

from pydantic import BaseModel

from imagetool.domain.models import Category, Listing, OcrResult, RunSpec


class SourceAdapter(Protocol):
    """Turns one Source's data into Listings. The only place that knows a site's format.

    `fetch` yields matching listings **newest first**, paging lazily; the RunService decides
    when to stop (Run mode, max_listings, max_scanned), so adapters must not cap the count.
    """

    name: str

    def fetch(self, spec: RunSpec) -> Iterable[Listing]: ...

    def fetch_image(self, url: str) -> bytes: ...


class OcrEngine(Protocol):
    def read(self, image: bytes, languages: list[str], image_url: str) -> OcrResult: ...


class ImageClassifier(Protocol):
    def score(self, image: bytes, image_url: str) -> Mapping[Category, float]: ...


class CardPrint(BaseModel):
    card_id: int
    card_name: str
    set_code: str
    set_name: str
    rarity: str | None = None


class CardNameMatch(BaseModel):
    card_id: int
    card_name: str
    matched_name: str
    language: str
    score: float


class CardCatalog(Protocol):
    def find_print(self, set_prefix: str, number: str) -> CardPrint | None: ...

    def set_name(self, set_prefix: str) -> str | None: ...

    def match_name(self, text_candidates: list[str]) -> CardNameMatch | None: ...

    def english_name(self, card_id: int) -> str | None: ...
