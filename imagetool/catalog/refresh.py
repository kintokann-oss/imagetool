"""Download the YGOPRODeck snapshot (D11). YGOPRODeck asks clients to cache data locally
and not call the API per lookup, which is exactly what this does: one download, then SQLite.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from pathlib import Path
from typing import Any

from imagetool.catalog.ygo import load_cardinfo, load_cardsets

API = "https://db.ygoprodeck.com/api/v7"
TRANSLATED_LANGUAGES = ("de", "fr", "it", "pt")
_USER_AGENT = "imagetool/0.1 (+catalog refresh)"


def _get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def refresh_from_api(connection: sqlite3.Connection) -> dict[str, int]:
    counts = {"sets": load_cardsets(connection, _get_json(f"{API}/cardsets.php"))}
    counts["en"] = load_cardinfo(connection, _get_json(f"{API}/cardinfo.php"), "en")
    for language in TRANSLATED_LANGUAGES:
        counts[language] = load_cardinfo(connection, _get_json(f"{API}/cardinfo.php?language={language}"), language)
    return counts


def load_from_directory(connection: sqlite3.Connection, directory: Path) -> dict[str, int]:
    """Load a snapshot saved as cardsets.json + cardinfo_<lang>.json (used for the bundled sample)."""
    counts: dict[str, int] = {}
    sets_file = directory / "cardsets.json"
    if sets_file.exists():
        counts["sets"] = load_cardsets(connection, json.loads(sets_file.read_text("utf-8")))
    for language in ("en", *TRANSLATED_LANGUAGES):
        file = directory / f"cardinfo_{language}.json"
        if file.exists():
            counts[language] = load_cardinfo(connection, json.loads(file.read_text("utf-8")), language)
    return counts
