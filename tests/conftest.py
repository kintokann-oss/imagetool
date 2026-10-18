from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from imagetool.catalog.refresh import load_from_directory
from imagetool.catalog.ygo import SqliteCardCatalog
from imagetool.config import DEFAULT_FIXTURES, Settings
from imagetool.db import connect, init_db
from imagetool.main import create_app


@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    """A private copy of the fixtures, so tests may edit listings.json."""
    target = tmp_path / "fixtures"
    shutil.copytree(DEFAULT_FIXTURES, target)
    return target


@pytest.fixture
def settings(tmp_path: Path, fixtures_dir: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "data" / "test.db",
        data_dir=tmp_path / "data",
        fixtures_dir=fixtures_dir,
        ocr_engine="fixture",
        image_classifier="fixture",
        tesseract_cmd=None,
        clip_model="unused",
        thumbnail_size=512,
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def catalog() -> SqliteCardCatalog:
    connection = connect(":memory:")
    init_db(connection)
    load_from_directory(connection, DEFAULT_FIXTURES / "ygoprodeck_sample")
    return SqliteCardCatalog(connection)
