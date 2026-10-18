"""Identifier registry: one Identifier per Category. Adding a category = adding an entry here."""

from __future__ import annotations

from collections.abc import Callable

from imagetool.domain.models import Category, ImageEvidence, ItemIdentity, Listing
from imagetool.domain.ports import CardCatalog
from imagetool.identify.board_game import identify_board_game
from imagetool.identify.electronics import identify_electronics
from imagetool.identify.vinyl import identify_vinyl
from imagetool.identify.yugioh import identify_yugioh

Identifier = Callable[[Listing, list[ImageEvidence], CardCatalog], ItemIdentity]

IDENTIFIERS: dict[Category, Identifier] = {
    Category.YUGIOH_CARD: identify_yugioh,
    Category.VINYL: identify_vinyl,
    Category.BOARD_GAME: identify_board_game,
    Category.ELECTRONICS: identify_electronics,
}


def identify(category: Category, listing: Listing, images: list[ImageEvidence], catalog: CardCatalog) -> ItemIdentity:
    identifier = IDENTIFIERS.get(category)
    return identifier(listing, images, catalog) if identifier else ItemIdentity()
