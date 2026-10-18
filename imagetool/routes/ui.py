"""The basic web UI: one static page that calls the JSON API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from imagetool.domain.models import KNOWN_CATEGORIES, RunMode

router = APIRouter()
_INDEX = Path(__file__).resolve().parent.parent / "web" / "index.html"


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_INDEX, media_type="text/html")


@router.get("/options")
def options(request: Request) -> dict[str, Any]:
    """What the UI form can offer: sources, categories, modes."""
    return {
        "sources": sorted(request.app.state.container.run_service.adapters),
        "categories": [category.value for category in KNOWN_CATEGORIES],
        "modes": [mode.value for mode in RunMode],
    }
