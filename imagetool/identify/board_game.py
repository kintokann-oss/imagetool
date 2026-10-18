"""Board game identification: title, publisher, language edition."""

from __future__ import annotations

from imagetool.domain.models import ImageEvidence, ItemIdentity, Listing
from imagetool.identify.common import find_known, strip_noise
from imagetool.text.language import detect_language

# Titles sellers write in the six markets, with local names mapped to the canonical title.
GAMES: dict[str, list[str]] = {
    "Catan": ["Catan", "Settlers of Catan", "Die Siedler von Catan", "Κατάν", "Катан", "Colonistii din Catan", "Catani asustajad"],
    "Carcassonne": ["Carcassonne", "Καρκασόν", "Каркасон"],
    "Ticket to Ride": ["Ticket to Ride", "Ticket to Ride Europe", "Zug um Zug", "Билет за влак"],
    "Monopoly": ["Monopoly", "Μονόπολη", "Монополи", "Monopol"],
    "Dixit": ["Dixit", "Ντίξιτ", "Диксит"],
    "Azul": ["Azul"],
    "Pandemic": ["Pandemic", "Πανδημία", "Пандемия"],
    "Risk": ["Risk", "Ρίσκο", "Риск", "Rizik"],
    "Scrabble": ["Scrabble", "Скрабъл"],
    "Codenames": ["Codenames", "Κωδικές Ονομασίες", "Кодови имена"],
    "7 Wonders": ["7 Wonders", "7 Θαύματα"],
    "Splendor": ["Splendor"],
    "Terraforming Mars": ["Terraforming Mars"],
    "Wingspan": ["Wingspan"],
    "Gloomhaven": ["Gloomhaven"],
}
PUBLISHERS = [
    "Kosmos", "Hasbro", "Days of Wonder", "Asmodee", "Kaissa", "Z-Man Games", "Z-Man",
    "Hans im Glück", "Repos Production", "Libellud", "Stonemaier", "Fantasy Flight",
    "Mattel", "Ravensburger", "Feuerland", "Fantasmagoria", "Lex Games", "Brain Games",
]
_EDITION_HINTS = {"1st edition": ["1st edition"], "2nd edition": ["2nd edition"], "5th edition": ["5th edition"]}


def identify_board_game(listing: Listing, images: list[ImageEvidence], _catalog: object) -> ItemIdentity:
    identity = ItemIdentity()
    ocr_text = "\n".join(image.ocr.text for image in images)
    text = f"{listing.title}\n{listing.description}\n{ocr_text}"

    aliases = {alias: canonical for canonical, names in GAMES.items() for alias in names}
    alias = find_known(text, list(aliases))
    if alias:
        identity.set("title", aliases[alias], 0.85, "dictionary")
    else:
        identity.set("title", strip_noise(listing.title), 0.4, "listing_title")

    identity.set("publisher", find_known(text, PUBLISHERS), 0.8, "dictionary")
    for edition, phrases in _EDITION_HINTS.items():
        if find_known(text, phrases):
            identity.set("edition", edition, 0.7, "text")
            break
    # Language of the components: non-English box text is strong evidence. Latin-only box text
    # (often just the game's name) says little, so fall back to the seller's language.
    box_language = detect_language(ocr_text) if ocr_text.strip() else "en"
    if box_language != "en":
        identity.set("language_edition", box_language, 0.7, "ocr_language")
    else:
        identity.set("language_edition", detect_language(f"{listing.title}\n{listing.description}"), 0.4, "listing_language")
    return identity
