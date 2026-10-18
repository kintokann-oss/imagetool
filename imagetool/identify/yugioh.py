"""Yu-Gi-Oh identification (D7, D11, D15): card name + set, print language, edition.

The set code printed under the artwork (e.g. LOB-EN001) is the primary key; the card
name read from the name bar / title is used to confirm it, or to find the card when no
set code is readable.
"""

from __future__ import annotations

import re

from imagetool.domain.models import ImageEvidence, ItemIdentity, Listing
from imagetool.domain.ports import CardCatalog
from imagetool.text.normalize import normalize

_LANG_CODES = "EN|DE|FR|IT|SP|PT|JP|JA|KR|AE|E|G|F|I|S|P"
SET_CODE_PATTERN = re.compile(rf"\b([A-Z0-9]{{2,4}})-({_LANG_CODES})?([0-9OIl]{{3}})\b", re.IGNORECASE)

PRINT_LANGUAGES = {
    "": "en", "EN": "en", "E": "en",
    "DE": "de", "G": "de",
    "FR": "fr", "F": "fr",
    "IT": "it", "I": "it",
    "SP": "es", "S": "es",
    "PT": "pt", "P": "pt",
    "JP": "ja", "JA": "ja",
    "KR": "ko",
    "AE": "en",
}

_EDITIONS = {
    "1st edition": [
        "1st edition", "1st ed", "first edition", "1 edition",
        "1 auflage", "1ere edition", "1re edition", "1a edizione", "1 edicion", "1 edicao",
        "1η εκδοση", "1 εκδοση", "πρωτη εκδοση", "1во издание", "първо издание",
        "1 izdanje", "prvo izdanje", "prima editie", "editia 1", "1 valjaanne", "esimene trukk",
    ],
    "limited edition": ["limited edition", "limitierte auflage", "edition limitee", "edizione limitata"],
    "unlimited": ["unlimited", "unlimited edition"],
}
_NORMALIZED_EDITIONS = [(edition, normalize(phrase)) for edition, phrases in _EDITIONS.items() for phrase in phrases]
_OCR_DIGIT_FIXES = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1"})


def find_set_code(text: str) -> tuple[str, str, str] | None:
    """Returns (prefix, language letters, number) of the first set code in the text."""
    match = SET_CODE_PATTERN.search(text)
    if not match:
        return None
    prefix, lang, number = match.groups()
    return prefix.upper(), (lang or "").upper(), number.translate(_OCR_DIGIT_FIXES)


def find_edition(text: str) -> str | None:
    normalized = f" {normalize(text)} "
    for edition, phrase in _NORMALIZED_EDITIONS:
        if f" {phrase} " in normalized:
            return edition
    return None


def _name_candidates(listing: Listing, images: list[ImageEvidence]) -> list[str]:
    candidates = [line for image in images for line in image.ocr.lines if line.strip()]
    candidates.append(listing.title)
    return candidates


def identify_yugioh(listing: Listing, images: list[ImageEvidence], catalog: CardCatalog) -> ItemIdentity:
    identity = ItemIdentity()
    ocr_text = "\n".join(image.ocr.text for image in images)
    all_text = f"{ocr_text}\n{listing.title}\n{listing.description}"

    set_code = find_set_code(ocr_text) or find_set_code(f"{listing.title}\n{listing.description}")
    code_origin = "ocr" if find_set_code(ocr_text) else "text"
    name_match = catalog.match_name(_name_candidates(listing, images))

    if set_code:
        prefix, lang, number = set_code
        identity.set("set_code", f"{prefix}-{lang}{number}", 0.9, f"pattern:{code_origin}")
        identity.set("print_language", PRINT_LANGUAGES.get(lang, "en"), 0.9, "set_code")
        card_print = catalog.find_print(prefix, number)
        if card_print:
            agrees = name_match is not None and name_match.card_id == card_print.card_id
            disagrees = name_match is not None and not agrees
            confidence = 0.98 if agrees else (0.6 if disagrees else 0.9)
            identity.set("card_name", card_print.card_name, confidence, "catalog:set_code")
            identity.set("set_name", card_print.set_name, 0.95, "catalog:set_code")
            identity.set("rarity", card_print.rarity, 0.7, "catalog:set_code")
            if disagrees and name_match:
                identity.set("name_read_as", name_match.card_name, name_match.score, "catalog:name")
        else:
            identity.set("set_name", catalog.set_name(prefix), 0.8, "catalog:set_prefix")

    if "card_name" not in identity.fields and name_match:
        identity.set("card_name", name_match.card_name, name_match.score * 0.9, f"catalog:name[{name_match.language}]")
        if "print_language" not in identity.fields:
            identity.set("print_language", name_match.language, 0.6, "name_language")

    identity.set("edition", find_edition(all_text), 0.8, "text")
    return identity
