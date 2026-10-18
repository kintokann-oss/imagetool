"""SQLite connection + migration runner."""

from __future__ import annotations

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        connection.execute("PRAGMA journal_mode = WAL")  # API reads while a Run writes
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    """Apply migrations/*.sql in filename order, each exactly once."""
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
    applied = {row["name"] for row in connection.execute("SELECT name FROM schema_migrations")}
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration.name in applied:
            continue
        connection.executescript(migration.read_text("utf-8"))
        connection.execute("INSERT INTO schema_migrations (name) VALUES (?)", (migration.name,))
    connection.commit()
