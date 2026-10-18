"""SQL for runs, listings, images and classifications. Parameterized queries only."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from imagetool.domain.models import Classification, ImageEvidence, Listing, RunSpec

RUN_COUNTERS = ("fetched", "skipped_unchanged", "classified", "unknown", "failed")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# -- runs ----------------------------------------------------------------------------------


def create_run(connection: sqlite3.Connection, spec: RunSpec) -> int:
    cursor = connection.execute("INSERT INTO runs (spec_json, status) VALUES (?, 'pending')", (spec.model_dump_json(),))
    connection.commit()
    return int(cursor.lastrowid)


def mark_run_running(connection: sqlite3.Connection, run_id: int) -> None:
    connection.execute("UPDATE runs SET status = 'running', started_at = ? WHERE id = ?", (_now(), run_id))
    connection.commit()


def finish_run(connection: sqlite3.Connection, run_id: int, counters: dict[str, int], error: str | None = None) -> None:
    connection.execute(
        """UPDATE runs SET status = ?, finished_at = ?, fetched = ?, skipped_unchanged = ?,
                  classified = ?, unknown = ?, failed = ?, error = ? WHERE id = ?""",
        ("failed" if error else "done", _now(), *(counters.get(name, 0) for name in RUN_COUNTERS), error, run_id),
    )
    connection.commit()


def get_run(connection: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        return None
    run = dict(row)
    run["spec"] = json.loads(run.pop("spec_json"))
    return run


def list_runs(connection: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = connection.execute("SELECT id FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [run for row in rows if (run := get_run(connection, row["id"]))]


def get_thumbnail_path(connection: sqlite3.Connection, listing_id: int, position: int) -> str | None:
    row = connection.execute(
        "SELECT thumbnail_path FROM listing_images WHERE listing_id = ? AND position = ?", (listing_id, position)
    ).fetchone()
    return row["thumbnail_path"] if row else None


def get_run_spec(connection: sqlite3.Connection, run_id: int) -> RunSpec:
    row = connection.execute("SELECT spec_json FROM runs WHERE id = ?", (run_id,)).fetchone()
    return RunSpec.model_validate_json(row["spec_json"])


# -- listings ------------------------------------------------------------------------------


def find_listing(connection: sqlite3.Connection, source: str, source_listing_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, content_hash, price FROM listings WHERE source = ? AND source_listing_id = ?",
        (source, source_listing_id),
    ).fetchone()


def touch_listing(connection: sqlite3.Connection, listing_id: int, run_id: int) -> None:
    connection.execute("UPDATE listings SET last_seen_run_id = ? WHERE id = ?", (run_id, listing_id))
    connection.commit()


def upsert_listing(
    connection: sqlite3.Connection, listing: Listing, language: str, content_hash: str, run_id: int
) -> int:
    values = (
        listing.title, listing.description, listing.price, listing.currency, listing.country,
        listing.posted_at.isoformat() if listing.posted_at else None, listing.source_url, language,
        json.dumps(listing.raw_attributes, ensure_ascii=False), content_hash, run_id,
    )
    existing = find_listing(connection, listing.source, listing.source_listing_id)
    if existing:
        listing_id = int(existing["id"])
        connection.execute(
            """UPDATE listings SET title = ?, description = ?, price = ?, currency = ?, country = ?, posted_at = ?,
                      source_url = ?, language = ?, raw_attributes_json = ?, content_hash = ?, last_seen_run_id = ?
               WHERE id = ?""",
            (*values, listing_id),
        )
    else:
        cursor = connection.execute(
            """INSERT INTO listings (title, description, price, currency, country, posted_at, source_url, language,
                                     raw_attributes_json, content_hash, last_seen_run_id, source, source_listing_id,
                                     first_seen_run_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*values, listing.source, listing.source_listing_id, run_id),
        )
        listing_id = int(cursor.lastrowid)
    connection.execute(
        "INSERT INTO listing_prices (listing_id, run_id, price, currency) VALUES (?, ?, ?, ?)",
        (listing_id, run_id, listing.price, listing.currency),
    )
    return listing_id


def replace_images(connection: sqlite3.Connection, listing_id: int, images: list[ImageEvidence]) -> None:
    connection.execute("DELETE FROM listing_images WHERE listing_id = ?", (listing_id,))
    for position, image in enumerate(images):
        connection.execute(
            """INSERT INTO listing_images (listing_id, position, source_url, thumbnail_path, ocr_text,
                                           ocr_lines_json, category_scores_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                listing_id, position, image.source_url, image.thumbnail_path, image.ocr.text,
                json.dumps(image.ocr.lines, ensure_ascii=False),
                json.dumps({str(category): score for category, score in image.category_scores.items()}),
            ),
        )


def save_classification(
    connection: sqlite3.Connection, listing_id: int, run_id: int, classification: Classification
) -> int:
    cursor = connection.execute(
        """INSERT INTO classifications (listing_id, run_id, category, confidence, is_bundle,
                                        estimated_item_count, identity_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            listing_id, run_id, classification.category.value, classification.confidence,
            int(classification.is_bundle), classification.estimated_item_count,
            classification.identity.model_dump_json(), _now(),
        ),
    )
    classification_id = int(cursor.lastrowid)
    connection.executemany(
        "INSERT INTO signals (classification_id, kind, category, weight, detail) VALUES (?, ?, ?, ?, ?)",
        [(classification_id, s.kind.value, s.category.value, s.weight, s.detail) for s in classification.signals],
    )
    return classification_id


# -- reads ---------------------------------------------------------------------------------


def _classification_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["is_bundle"] = bool(result["is_bundle"])
    result["identity"] = json.loads(result.pop("identity_json"))["fields"]
    return result


def list_classifications(connection: sqlite3.Connection, run_id: int, category: str | None) -> list[dict[str, Any]]:
    query = """SELECT c.id, c.listing_id, c.category, c.confidence, c.is_bundle, c.estimated_item_count,
                      c.identity_json, l.title, l.price, l.currency, l.country, l.language, l.source_url,
                      l.posted_at, (SELECT COUNT(*) FROM listing_images i WHERE i.listing_id = l.id) AS image_count
               FROM classifications c JOIN listings l ON l.id = c.listing_id
               WHERE c.run_id = ?"""
    params: list[Any] = [run_id]
    if category:
        query += " AND c.category = ?"
        params.append(category)
    rows = connection.execute(query + " ORDER BY c.id", params).fetchall()
    return [_classification_row(row) for row in rows]


def get_listing_detail(connection: sqlite3.Connection, listing_id: int) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if not row:
        return None
    listing = dict(row)
    listing["raw_attributes"] = json.loads(listing.pop("raw_attributes_json"))
    listing["images"] = [
        {
            "position": image["position"],
            "source_url": image["source_url"],
            "thumbnail_path": image["thumbnail_path"],
            "ocr_text": image["ocr_text"],
            "category_scores": json.loads(image["category_scores_json"]),
        }
        for image in connection.execute(
            "SELECT * FROM listing_images WHERE listing_id = ? ORDER BY position", (listing_id,)
        )
    ]
    listing["prices"] = [
        dict(price)
        for price in connection.execute(
            "SELECT run_id, price, currency FROM listing_prices WHERE listing_id = ? ORDER BY id", (listing_id,)
        )
    ]
    latest = connection.execute(
        """SELECT id, run_id, category, confidence, is_bundle, estimated_item_count, identity_json
           FROM classifications WHERE listing_id = ? ORDER BY id DESC LIMIT 1""",
        (listing_id,),
    ).fetchone()
    if latest:
        classification = _classification_row(latest)
        classification["signals"] = [
            dict(signal)
            for signal in connection.execute(
                "SELECT kind, category, weight, detail FROM signals WHERE classification_id = ? ORDER BY id",
                (latest["id"],),
            )
        ]
        listing["classification"] = classification
    else:
        listing["classification"] = None
    return listing
