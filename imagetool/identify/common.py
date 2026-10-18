"""Small helpers shared by Identifiers."""

from __future__ import annotations

import re

from imagetool.text.normalize import contains_term, normalize

_NOISE = re.compile(
    r"\b(?:vinyl|lp|2lp|new|sealed|mint|nm|vg\+?|used|original|orig|1st press|first press|"
    r"disc de vinil|disc vinil|vinil|δίσκος βινυλίου|δίσκος|βινύλιο|плоча|винил|ploča|vinüülplaat|"
    r"πωλείται|πωλειται|продавам|prodajem|vand|vând|müüa|müüs)\b",
    re.IGNORECASE,
)
_SPACES = re.compile(r"\s+")


def strip_noise(text: str) -> str:
    return _SPACES.sub(" ", _NOISE.sub(" ", text)).strip(" ,.;/")


def find_known(text: str, names: list[str]) -> str | None:
    """First known name (longest first) contained in the text, ignoring case and accents."""
    normalized = normalize(text)
    for name in sorted(names, key=len, reverse=True):
        if contains_term(normalized, normalize(name)):
            return name
    return None
