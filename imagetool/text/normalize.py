"""Text normalization so keyword matching ignores case, accents and punctuation."""

from __future__ import annotations

import re
import unicodedata

_NON_WORD = re.compile(r"[^\w\"']+", re.UNICODE)
_SPACES = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize(text: str) -> str:
    """Casefold, drop accents/diacritics, turn punctuation into spaces, collapse spaces."""
    folded = strip_accents(text.casefold())
    return _SPACES.sub(" ", _NON_WORD.sub(" ", folded)).strip()


def contains_term(normalized_text: str, normalized_term: str) -> bool:
    """Word-boundary match of an already-normalized term inside already-normalized text."""
    if not normalized_term:
        return False
    return f" {normalized_term} " in f" {normalized_text} "
