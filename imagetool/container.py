"""Wires settings → database, engines, adapters, catalog → RunService."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from imagetool.catalog.refresh import load_from_directory
from imagetool.catalog.ygo import SqliteCardCatalog, catalog_is_empty
from imagetool.classify.keywords import default_dictionary
from imagetool.config import Settings
from imagetool.db import connect, init_db
from imagetool.engines import build_image_classifier, build_ocr_engine
from imagetool.images.store import ImageStore
from imagetool.services.run_service import RunService
from imagetool.sources import build_source_adapters


@dataclass
class Container:
    settings: Settings
    connect: Callable[[], sqlite3.Connection]
    run_service: RunService


def build_container(settings: Settings) -> Container:
    connect_db = partial(connect, settings.database_path)
    setup = connect_db()
    init_db(setup)
    if catalog_is_empty(setup):
        # Until `catalog refresh` has run, use the bundled sample so the pipeline works end to end.
        load_from_directory(setup, settings.fixtures_dir / "ygoprodeck_sample")
    setup.close()

    run_service = RunService(
        connect=connect_db,
        adapters=build_source_adapters(settings),
        ocr=build_ocr_engine(settings),
        image_classifier=build_image_classifier(settings),
        # Read-only catalog connection, shared by Runs (which execute one at a time).
        catalog=SqliteCardCatalog(connect_db()),
        image_store=ImageStore(settings.data_dir / "images", settings.thumbnail_size),
        dictionary=default_dictionary(),
    )
    return Container(settings=settings, connect=connect_db, run_service=run_service)
