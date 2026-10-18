"""Yu-Gi-Oh card Catalog over a local YGOPRODeck snapshot in SQLite (D11, D15)."""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from imagetool.domain.ports import CardNameMatch, CardPrint
from imagetool.text.normalize import normalize

_SET_CODE = re.compile(r"^([A-Z0-9]{2,5})-([A-Z]{0,2})(\d{3})$")
MIN_NAME_SCORE = 0.82
MAX_WINDOW_WORDS = 8
# Words too common in card names to narrow down candidates on their own.
_COMMON_TOKENS = {"the", "of", "and", "a", "dragon", "der", "die", "le", "la", "de", "du", "di", "il"}


def split_set_code(set_code: str) -> tuple[str, str] | None:
    match = _SET_CODE.match(set_code.strip().upper())
    return (match.group(1), match.group(3)) if match else None


@dataclass(frozen=True)
class _Name:
    card_id: int
    language: str
    name: str
    normalized: str
    word_count: int


class SqliteCardCatalog:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._names: list[_Name] | None = None
        self._by_normalized: dict[str, list[_Name]] = {}
        self._by_token: dict[str, list[_Name]] = defaultdict(list)

    # -- lookups ---------------------------------------------------------------------------

    def find_print(self, set_prefix: str, number: str) -> CardPrint | None:
        row = self._connection.execute(
            """SELECT p.card_id, c.name, p.set_code, p.set_name, p.rarity
               FROM ygo_prints p JOIN ygo_cards c ON c.id = p.card_id
               WHERE p.set_prefix = ? AND p.number = ?
               ORDER BY p.set_code LIMIT 1""",
            (set_prefix.upper(), number),
        ).fetchone()
        if not row:
            return None
        return CardPrint(
            card_id=row["card_id"],
            card_name=row["name"],
            set_code=row["set_code"],
            set_name=row["set_name"],
            rarity=row["rarity"],
        )

    def set_name(self, set_prefix: str) -> str | None:
        row = self._connection.execute(
            "SELECT set_name FROM ygo_sets WHERE set_prefix = ?", (set_prefix.upper(),)
        ).fetchone()
        if row:
            return row["set_name"]
        row = self._connection.execute(
            "SELECT set_name FROM ygo_prints WHERE set_prefix = ? LIMIT 1", (set_prefix.upper(),)
        ).fetchone()
        return row["set_name"] if row else None

    def english_name(self, card_id: int) -> str | None:
        row = self._connection.execute("SELECT name FROM ygo_cards WHERE id = ?", (card_id,)).fetchone()
        return row["name"] if row else None

    def match_name(self, text_candidates: list[str]) -> CardNameMatch | None:
        """Best card whose name (any language) appears, possibly misread by OCR, in the candidates."""
        self._ensure_index()
        best: CardNameMatch | None = None
        for candidate in text_candidates:
            words = normalize(candidate).split()
            for size in range(min(MAX_WINDOW_WORDS, len(words)), 0, -1):
                for start in range(len(words) - size + 1):
                    window = " ".join(words[start : start + size])
                    match = self._match_window(window, size)
                    if match and (best is None or (match.score, len(match.matched_name)) > (best.score, len(best.matched_name))):
                        best = match
        return best

    # -- internals -------------------------------------------------------------------------

    def _ensure_index(self) -> None:
        if self._names is not None:
            return
        rows = self._connection.execute(
            "SELECT n.card_id, n.language, n.name, n.normalized_name FROM ygo_card_names n"
        ).fetchall()
        self._names = []
        for row in rows:
            entry = _Name(row["card_id"], row["language"], row["name"], row["normalized_name"], len(row["normalized_name"].split()))
            self._names.append(entry)
            self._by_normalized.setdefault(entry.normalized, []).append(entry)
            for token in set(entry.normalized.split()):
                if token not in _COMMON_TOKENS:
                    self._by_token[token].append(entry)

    def _to_match(self, entry: _Name, score: float) -> CardNameMatch:
        english = self.english_name(entry.card_id) or entry.name
        return CardNameMatch(card_id=entry.card_id, card_name=english, matched_name=entry.name, language=entry.language, score=round(score, 3))

    def _match_window(self, window: str, size: int) -> CardNameMatch | None:
        exact = self._by_normalized.get(window)
        if exact:
            entry = sorted(exact, key=lambda name: name.language != "en")[0]
            return self._to_match(entry, 1.0)
        if len(window) < 6:
            return None
        candidates: dict[tuple[int, str], _Name] = {}
        for token in window.split():
            for entry in self._by_token.get(token, ()):
                candidates[(entry.card_id, entry.language)] = entry
        best_entry, best_score = None, 0.0
        for entry in candidates.values():
            if abs(entry.word_count - size) > 1 or abs(len(entry.normalized) - len(window)) > 0.3 * len(entry.normalized):
                continue
            score = SequenceMatcher(None, window, entry.normalized).ratio()
            if score > best_score:
                best_entry, best_score = entry, score
        if best_entry and best_score >= MIN_NAME_SCORE:
            return self._to_match(best_entry, best_score)
        return None


# -- loading ---------------------------------------------------------------------------------


def load_cardinfo(connection: sqlite3.Connection, payload: dict[str, Any], language: str = "en") -> int:
    """Load a YGOPRODeck `cardinfo.php` response. English loads cards + prints; other languages add names."""
    cards = payload.get("data", [])
    for card in cards:
        card_id, name = int(card["id"]), card["name"]
        if language == "en":
            connection.execute(
                "INSERT INTO ygo_cards (id, name) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET name = excluded.name",
                (card_id, name),
            )
            connection.execute("DELETE FROM ygo_prints WHERE card_id = ?", (card_id,))
            for card_set in card.get("card_sets", []) or []:
                split = split_set_code(card_set.get("set_code", ""))
                if not split:
                    continue
                connection.execute(
                    "INSERT INTO ygo_prints (card_id, set_prefix, number, set_code, set_name, rarity) VALUES (?, ?, ?, ?, ?, ?)",
                    (card_id, split[0], split[1], card_set["set_code"], card_set.get("set_name", ""), card_set.get("set_rarity")),
                )
        elif not connection.execute("SELECT 1 FROM ygo_cards WHERE id = ?", (card_id,)).fetchone():
            continue
        connection.execute(
            """INSERT INTO ygo_card_names (card_id, language, name, normalized_name) VALUES (?, ?, ?, ?)
               ON CONFLICT(card_id, language) DO UPDATE SET name = excluded.name, normalized_name = excluded.normalized_name""",
            (card_id, language, name, normalize(name)),
        )
    connection.commit()
    return len(cards)


def load_cardsets(connection: sqlite3.Connection, payload: list[dict[str, Any]]) -> int:
    """Load a YGOPRODeck `cardsets.php` response (set prefix → set name)."""
    for card_set in payload:
        prefix = (card_set.get("set_code") or "").strip().upper()
        if prefix:
            connection.execute(
                "INSERT INTO ygo_sets (set_prefix, set_name) VALUES (?, ?) ON CONFLICT(set_prefix) DO UPDATE SET set_name = excluded.set_name",
                (prefix, card_set.get("set_name", "")),
            )
    connection.commit()
    return len(payload)


def catalog_is_empty(connection: sqlite3.Connection) -> bool:
    return connection.execute("SELECT 1 FROM ygo_cards LIMIT 1").fetchone() is None
