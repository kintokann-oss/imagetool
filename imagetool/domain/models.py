"""Domain models shared by every layer. See grilling-output.md §2 for the vocabulary."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Category(StrEnum):
    VINYL = "vinyl"
    YUGIOH_CARD = "yugioh_card"
    BOARD_GAME = "board_game"
    ELECTRONICS = "electronics"
    UNKNOWN = "unknown"


KNOWN_CATEGORIES: tuple[Category, ...] = (
    Category.VINYL,
    Category.YUGIOH_CARD,
    Category.BOARD_GAME,
    Category.ELECTRONICS,
)


class SignalKind(StrEnum):
    TITLE_KEYWORD = "title_keyword"
    DESCRIPTION_KEYWORD = "description_keyword"
    OCR_KEYWORD = "ocr_keyword"
    IMAGE_LABEL = "image_label"
    SOURCE_CATEGORY = "source_category"
    PATTERN = "pattern"


class Listing(BaseModel):
    """One used-item post from a Source, normalized by its Source Adapter."""

    source: str
    source_listing_id: str
    title: str
    description: str = ""
    price: float | None = None
    currency: str = "EUR"
    country: str | None = None
    posted_at: date | None = None
    source_url: str = ""
    image_urls: list[str] = Field(default_factory=list)
    raw_attributes: dict[str, str] = Field(default_factory=dict)


class PriceRange(BaseModel):
    min: float | None = None
    max: float | None = None
    currency: str = "EUR"


class RunMode(StrEnum):
    # Newest first; stop at the first listing already stored (what a notifier does).
    NEW_ONLY = "new_only"
    # Keep going past stored listings to find older ones never classified.
    BACKFILL = "backfill"


class RunSpec(BaseModel):
    """The user-set conditions of a Run."""

    source: str = "mock_marketplace"
    mode: RunMode = RunMode.BACKFILL
    query: str | None = None
    categories: list[Category] = Field(default_factory=lambda: list(KNOWN_CATEGORIES))
    countries: list[str] | None = None
    price: PriceRange | None = None
    posted_after: date | None = None
    max_listings: int = Field(default=100, ge=1, le=10_000)  # listings classified per Run
    max_scanned: int = Field(default=1_000, ge=1, le=100_000)  # listings looked at per Run, seen or not
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class Signal(BaseModel):
    """One piece of evidence for a Category, with where it came from."""

    kind: SignalKind
    category: Category
    weight: float
    detail: str


class IdentityField(BaseModel):
    value: str
    confidence: float
    origin: str


class ItemIdentity(BaseModel):
    """Category-specific fields naming the exact item, e.g. card_name / set_code."""

    fields: dict[str, IdentityField] = Field(default_factory=dict)

    def set(self, name: str, value: str | None, confidence: float, origin: str) -> None:
        if value:
            self.fields[name] = IdentityField(value=value, confidence=round(confidence, 3), origin=origin)

    def value(self, name: str) -> str | None:
        field = self.fields.get(name)
        return field.value if field else None

    def as_values(self) -> dict[str, str]:
        return {name: field.value for name, field in self.fields.items()}


class Classification(BaseModel):
    category: Category
    confidence: float
    is_bundle: bool = False
    estimated_item_count: int | None = None
    identity: ItemIdentity = Field(default_factory=ItemIdentity)
    signals: list[Signal] = Field(default_factory=list)


class OcrResult(BaseModel):
    """Raw text produced by an OcrEngine for one image (stored, see D16)."""

    text: str
    lines: list[str] = Field(default_factory=list)


class ImageEvidence(BaseModel):
    """What the engines saw in one image of a Listing."""

    source_url: str
    ocr: OcrResult
    category_scores: dict[Category, float] = Field(default_factory=dict)
    thumbnail_path: str | None = None


def model_to_json(model: BaseModel) -> str:
    return model.model_dump_json()


def json_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
