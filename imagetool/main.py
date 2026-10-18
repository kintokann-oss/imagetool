"""FastAPI app factory. Run with:  uvicorn imagetool.main:create_app --factory --reload"""

from __future__ import annotations

from fastapi import FastAPI

from imagetool.config import Settings, load_settings
from imagetool.container import build_container
from imagetool.routes import health, listings, runs, ui


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="imagetool", version="0.1.0")
    app.state.container = build_container(settings or load_settings())
    app.include_router(health.router)
    app.include_router(runs.router)
    app.include_router(listings.router)
    app.include_router(ui.router)
    return app

