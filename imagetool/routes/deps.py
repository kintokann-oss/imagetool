"""Shared route dependencies."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from fastapi import Request


def db_connection(request: Request) -> Iterator[sqlite3.Connection]:
    """One connection per request, closed afterwards."""
    connection = request.app.state.container.connect()
    try:
        yield connection
    finally:
        connection.close()
