"""RunService: fetch → dedupe → engines → classify → identify → persist, for one Run."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from imagetool.classify import classify_listing
from imagetool.classify.keywords import KeywordDictionary
from imagetool.domain.models import Category, ImageEvidence, Listing, RunMode, RunSpec
from imagetool.domain.ports import CardCatalog, ImageClassifier, OcrEngine, SourceAdapter
from imagetool.images.store import ImageStore
from imagetool.services import repository
from imagetool.text.language import detect_language, ocr_languages

log = logging.getLogger(__name__)


def content_hash(listing: Listing) -> str:
    """Hash of what the seller wrote and showed; together with price it decides skip vs re-classify (D8)."""
    payload = "\x1f".join([listing.title, listing.description, *listing.image_urls])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_unchanged(existing: sqlite3.Row | None, listing: Listing, listing_hash: str) -> bool:
    return existing is not None and existing["content_hash"] == listing_hash and existing["price"] == listing.price


@dataclass
class RunService:
    """Each Run uses its own connection; Runs execute one at a time (one GPU, one SQLite writer)."""

    connect: Callable[[], sqlite3.Connection]
    adapters: dict[str, SourceAdapter]
    ocr: OcrEngine
    image_classifier: ImageClassifier
    catalog: CardCatalog
    image_store: ImageStore
    dictionary: KeywordDictionary
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def create_run(self, spec: RunSpec) -> int:
        if spec.source not in self.adapters:
            raise ValueError(f"unknown source '{spec.source}', available: {sorted(self.adapters)}")
        connection = self.connect()
        try:
            return repository.create_run(connection, spec)
        finally:
            connection.close()

    def execute(self, run_id: int) -> None:
        with self._lock:
            connection = self.connect()
            try:
                self._execute(connection, run_id)
            finally:
                connection.close()

    def _execute(self, connection: sqlite3.Connection, run_id: int) -> None:
        spec = repository.get_run_spec(connection, run_id)
        adapter = self.adapters[spec.source]
        counters = dict.fromkeys(repository.RUN_COUNTERS, 0)
        repository.mark_run_running(connection, run_id)
        try:
            for listing in adapter.fetch(spec):
                if counters["fetched"] >= spec.max_scanned or counters["classified"] + counters["unknown"] >= spec.max_listings:
                    break
                already_seen = repository.find_listing(connection, listing.source, listing.source_listing_id) is not None
                if spec.mode == RunMode.NEW_ONLY and already_seen:
                    break  # newest first: everything from here on was seen by an earlier Run
                counters["fetched"] += 1
                try:
                    outcome = self._process(connection, run_id, spec, adapter, listing)
                except Exception:  # one bad listing must not kill the Run
                    log.exception("failed to process listing %s/%s", listing.source, listing.source_listing_id)
                    connection.rollback()
                    outcome = "failed"
                counters[outcome] += 1
        except Exception as error:
            log.exception("run %s failed", run_id)
            repository.finish_run(connection, run_id, counters, error=str(error))
            return
        repository.finish_run(connection, run_id, counters)

    def _process(self, connection: sqlite3.Connection, run_id: int, spec: RunSpec, adapter: SourceAdapter, listing: Listing) -> str:
        listing_hash = content_hash(listing)
        existing = repository.find_listing(connection, listing.source, listing.source_listing_id)
        if is_unchanged(existing, listing, listing_hash):
            repository.touch_listing(connection, existing["id"], run_id)
            return "skipped_unchanged"

        language = detect_language(f"{listing.title}\n{listing.description}")
        listing_id = repository.upsert_listing(connection, listing, language, listing_hash, run_id)
        images = [self._inspect_image(adapter, listing_id, position, url, language) for position, url in enumerate(listing.image_urls)]
        classification = classify_listing(listing, images, spec, self.dictionary, self.catalog)

        repository.replace_images(connection, listing_id, images)
        repository.save_classification(connection, listing_id, run_id, classification)
        connection.commit()
        return "unknown" if classification.category == Category.UNKNOWN else "classified"

    def _inspect_image(self, adapter: SourceAdapter, listing_id: int, position: int, url: str, language: str) -> ImageEvidence:
        image = adapter.fetch_image(url)
        ocr = self.ocr.read(image, ocr_languages(language), url)
        scores = dict(self.image_classifier.score(image, url))
        thumbnail = self.image_store.save_thumbnail(listing_id, position, image)
        return ImageEvidence(source_url=url, ocr=ocr, category_scores=scores, thumbnail_path=str(thumbnail))
