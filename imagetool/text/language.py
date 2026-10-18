"""Cheap listing-language detection for the six market languages (D2).

Script decides Greek / Cyrillic; Latin-script languages are told apart by their
distinctive letters and a few very common words. Good enough to pick OCR packs.
"""

from __future__ import annotations

import re

LANGUAGES = ("en", "el", "bg", "hr", "ro", "et")

# Tesseract language-pack codes per listing language.
TESSERACT_CODES = {"en": "eng", "el": "ell", "bg": "bul", "hr": "hrv", "ro": "ron", "et": "est"}

_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")

_LATIN_HINTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "hr": ("čćđšž", ("i", "je", "za", "sa", "prodajem", "stanje", "očuvan", "ploča")),
    "ro": ("ăâîșțşţ", ("și", "si", "de", "vand", "vând", "stare", "pentru", "foarte")),
    "et": ("õäöüšž", ("ja", "on", "müüa", "müüs", "korras", "hea", "seisukord", "väga")),
}


def detect_language(text: str) -> str:
    if not text.strip():
        return "en"
    greek = len(_GREEK.findall(text))
    cyrillic = len(_CYRILLIC.findall(text))
    if greek or cyrillic:
        return "el" if greek >= cyrillic else "bg"

    lowered = text.casefold()
    words = set(re.findall(r"\w+", lowered))
    best, best_score = "en", 0
    for lang, (letters, common_words) in _LATIN_HINTS.items():
        score = 2 * sum(lowered.count(letter) for letter in letters)
        score += sum(1 for word in common_words if word in words)
        if score > best_score:
            best, best_score = lang, score
    return best if best_score >= 2 else "en"


def ocr_languages(listing_language: str) -> list[str]:
    """Tesseract packs to use: the listing's language plus English (item text is often English)."""
    codes = [TESSERACT_CODES.get(listing_language, "eng")]
    if "eng" not in codes:
        codes.append("eng")
    return codes
