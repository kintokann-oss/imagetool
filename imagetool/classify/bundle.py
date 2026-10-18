"""Bundle / lot detection (D10): one Classification per Listing, flagged when it sells many items."""

from __future__ import annotations

import re

from imagetool.text.normalize import contains_term, normalize

BUNDLE_WORDS = [
    # en
    "lot", "bundle", "collection", "job lot", "joblot", "bulk",
    # el
    "συλλογη", "πακετο καρτων",
    # bg
    "колекция", "лот",
    # hr
    "kolekcija", "zbirka",
    # ro
    "colectie", "lot de",
    # et
    "kollektsioon",
]
_NORMALIZED_WORDS = [normalize(word) for word in BUNDLE_WORDS]

# "2LP" is a double album, not a bundle, so record units need at least 3.
_RECORD_UNIT = r"records|lps|lp|δισκοι|плочи|ploca|ploce|discuri|plaati|plaadid"
_UNIT = (
    r"pcs|pieces|cards|games|items|"
    r"καρτες|τεμαχια|τεμ|παιχνιδια|"
    r"карти|броя|бр|игри|"
    r"karata|karte|kartica|komada|kom|igre|"
    r"carti|cartonase|bucati|buc|jocuri|"
    r"kaarti|kaardid|tk|mangu"
)
# Allows one word between count and unit: "30 vinyl records", "50 holo cards".
_COUNT = re.compile(rf"\b(\d{{1,4}})\s*(?:x\s*)?(?:[^\W\d]+\s+)?(?:{_UNIT})\b")
_RECORD_COUNT = re.compile(rf"\b(\d{{1,4}})\s*(?:x\s*)?(?:[^\W\d]+\s+)?(?:{_RECORD_UNIT})\b")


def detect_bundle(title: str, description: str) -> tuple[bool, int | None]:
    text = normalize(f"{title} {description}")
    counts = [int(match) for match in _COUNT.findall(text) if int(match) >= 2]
    counts += [int(match) for match in _RECORD_COUNT.findall(text) if int(match) >= 3]
    count = max(counts, default=None)
    has_word = any(contains_term(text, word) for word in _NORMALIZED_WORDS)
    return (count is not None or has_word), count
