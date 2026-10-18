"""Listings: one Listing with its images, price history and latest Classification + Signals."""

from __future__ import annotations

import sqlite3
from typing import Annotated, Any

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from imagetool.routes.deps import db_connection
from imagetool.services import repository

router = APIRouter(prefix="/listings")


@router.get("/{listing_id}")
def get_listing(listing_id: int, connection: Annotated[sqlite3.Connection, Depends(db_connection)]) -> dict[str, Any]:
    listing = repository.get_listing_detail(connection, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="listing not found")
    return listing


@router.get("/{listing_id}/images/{position}")
def get_listing_image(
    listing_id: int, position: int, request: Request, connection: Annotated[sqlite3.Connection, Depends(db_connection)]
) -> FileResponse:
    """The stored 512 px copy (D14)."""
    stored = repository.get_thumbnail_path(connection, listing_id, position)
    images_root = (request.app.state.container.settings.data_dir / "images").resolve()
    path = Path(stored).resolve() if stored else None
    if not path or images_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="image not found")
    return FileResponse(path, media_type="image/jpeg")
