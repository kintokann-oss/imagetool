"""Keyword dictionaries per category × language (D6), loaded from keywords/*.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from imagetool.domain.models import KNOWN_CATEGORIES, Category
from imagetool.text.normalize import contains_term, normalize

_DIR = Path(__file__).parent / "keywords"


@dataclass(frozen=True)
class KeywordHit:
    category: Category
    term: str
    language: str


@dataclass(frozen=True)
class KeywordDictionary:
    # category -> list of (language, original term, normalized term), longest first
    terms: dict[Category, list[tuple[str, str, str]]]

    def find(self, text: str) -> list[KeywordHit]:
        normalized = normalize(text)
        hits: list[KeywordHit] = []
        for category, entries in self.terms.items():
            seen: set[str] = set()
            for language, term, norm_term in entries:
                if norm_term in seen or not contains_term(normalized, norm_term):
                    continue
                # skip a short term already covered by a longer matched term ("δίσκος" in "δίσκος βινυλίου")
                if any(f" {norm_term} " in f" {longer} " for longer in seen):
                    continue
                seen.add(norm_term)
                hits.append(KeywordHit(category, term, language))
        return hits


def load_dictionary(directory: Path = _DIR) -> KeywordDictionary:
    terms: dict[Category, list[tuple[str, str, str]]] = {}
    for category in KNOWN_CATEGORIES:
        raw: dict[str, list[str]] = json.loads((directory / f"{category.value}.json").read_text("utf-8"))
        entries = [(lang, term, normalize(term)) for lang, words in raw.items() for term in words]
        entries.sort(key=lambda entry: len(entry[2]), reverse=True)
        terms[category] = entries
    return KeywordDictionary(terms)


@cache
def default_dictionary() -> KeywordDictionary:
    return load_dictionary()
