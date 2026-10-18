"""Vinyl identification: artist, title, format, year, label, catalog number."""

from __future__ import annotations

import re

from imagetool.domain.models import ImageEvidence, ItemIdentity, Listing
from imagetool.identify.common import find_known, strip_noise

# International majors plus the regional state labels sellers in GR/HR/BG/RO/EE will list.
LABELS: dict[str, list[str]] = {
    **{name: [name] for name in (
        "Harvest", "EMI", "Columbia", "Parlophone", "Atlantic", "Capitol", "Decca", "Polydor",
        "Philips", "RCA", "CBS", "Island", "Virgin", "Apple Records", "Warner", "Elektra", "Mercury",
        "Jugoton", "PGP RTB", "Suzy", "Croatia Records", "Electrecord", "Minos", "Lyra",
    )},
    "Balkanton": ["Balkanton", "Балкантон"],
    "Melodiya": ["Melodiya", "Мелодия", "Melodija"],
}

_FORMATS = [
    (re.compile(r"\b2\s?lp\b|\bdouble lp\b|\b2x\s?lp\b", re.I), "2LP"),
    (re.compile(r"\blp\b|12\s?(?:\"|''|inch|in\b)", re.I), "LP"),
    (re.compile(r"7\s?(?:\"|''|inch|in\b)|\bsingle\b|\b45\s?rpm\b", re.I), "7\""),
    (re.compile(r"\bep\b", re.I), "EP"),
]
_YEAR = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
# "Artist - Title": a hyphen only separates when spaced, so "Jay-Z" stays one artist.
_SEPARATOR = re.compile(r"\s+[-:|]\s+|\s*[–—]\s*")
_BRACKETS = re.compile(r"[(\[].*?[)\]]")
_CATALOG_NO = re.compile(r"\b([A-Z]{2,6})[ -]?(\d{3,6})\b")
_NOT_CATALOG = {"LP", "EP", "RPM", "CD"}


def _artist_and_title(title: str) -> tuple[str, str] | None:
    parts = _SEPARATOR.split(strip_noise(_BRACKETS.sub(" ", title)), maxsplit=1)
    if len(parts) != 2:
        return None
    artist, album = (strip_noise(_YEAR.sub(" ", part)) for part in parts)
    return (artist, album) if artist and album else None


def _catalog_number(text: str) -> str | None:
    for match in _CATALOG_NO.finditer(text):
        letters, digits = match.groups()
        if letters not in _NOT_CATALOG and not _YEAR.fullmatch(digits):
            return f"{letters} {digits}"
    return None


def identify_vinyl(listing: Listing, images: list[ImageEvidence], _catalog: object) -> ItemIdentity:
    identity = ItemIdentity()
    ocr_text = "\n".join(image.ocr.text for image in images)
    text = f"{listing.title}\n{listing.description}"

    artist_title = _artist_and_title(listing.title)
    if artist_title:
        identity.set("artist", artist_title[0], 0.75, "title")
        identity.set("title", artist_title[1], 0.75, "title")

    for pattern, name in _FORMATS:
        if pattern.search(text) or pattern.search(ocr_text):
            identity.set("format", name, 0.8, "text")
            break

    year = _YEAR.search(text) or _YEAR.search(ocr_text)
    if year:
        identity.set("year", year.group(1), 0.6, "pattern")

    aliases = {alias: canonical for canonical, names in LABELS.items() for alias in names}
    label = find_known(f"{text}\n{ocr_text}", list(aliases))
    identity.set("label", aliases[label] if label else None, 0.8, "dictionary")

    catalog_no = _catalog_number(ocr_text) or _catalog_number(listing.description)
    identity.set("catalog_number", catalog_no, 0.6, "pattern")
    return identity
