"""Runs: start one from a Run Spec, read its status and its Classifications."""

from __future__ import annotations

from typing import Any

import sqlite3
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from imagetool.domain.models import Category, RunSpec
from imagetool.routes.deps import db_connection
from imagetool.services import repository

router = APIRouter(prefix="/runs")


class RunCreated(BaseModel):
    id: int
    status: str


Connection = Annotated[sqlite3.Connection, Depends(db_connection)]


@router.post("", status_code=202, response_model=RunCreated)
def start_run(spec: RunSpec, background: BackgroundTasks, request: Request) -> RunCreated:
    service = request.app.state.container.run_service
    try:
        run_id = service.create_run(spec)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    background.add_task(service.execute, run_id)
    return RunCreated(id=run_id, status="pending")


@router.get("")
def list_runs(connection: Connection, limit: int = 20) -> list[dict[str, Any]]:
    return repository.list_runs(connection, min(max(limit, 1), 200))


@router.get("/{run_id}")
def get_run(run_id: int, connection: Connection) -> dict[str, Any]:
    run = repository.get_run(connection, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/{run_id}/classifications")
def get_run_classifications(run_id: int, connection: Connection, category: Category | None = None) -> list[dict[str, Any]]:
    if not repository.get_run(connection, run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return repository.list_classifications(connection, run_id, category.value if category else None)
