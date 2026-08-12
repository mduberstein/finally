"""SQLite connections, lazy schema creation, and the unit-of-work primitive."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .seed import seed_defaults

DEFAULT_DB_PATH = "db/finally.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def database_path() -> Path:
    """The SQLite file location, from DB_PATH or the packaged default."""
    return Path(os.environ.get("DB_PATH") or DEFAULT_DB_PATH)


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open a WAL-mode connection with rows addressable by column name.

    Transactions are driven explicitly by `transaction`, so the connection is
    left in autocommit mode. Never share the result across threads.
    """
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def initialize(path: Path | None = None) -> None:
    """Create and seed the database if it has no tables yet.

    Safe to call repeatedly and safe on a database that already holds data:
    once the tables exist nothing is written, so a user who removes a seeded
    ticker does not get it back on the next start.
    """
    conn = connect(path)
    try:
        _ensure_schema(conn)
    finally:
        conn.close()


@contextmanager
def transaction(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """A unit of work: one connection, committed on success, rolled back on error.

    Every repository function takes the connection this yields. Wrapping
    several of them in one block makes them atomic, so a trade cannot debit
    cash without also recording the position and the trade log.

    The block holds a write lock for its duration. Keep it short and never
    await a network call inside one.
    """
    conn = connect(path)
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Apply schema.sql and the seed rows when the database is empty."""
    if _has_tables(conn):
        return
    conn.executescript(SCHEMA_PATH.read_text())
    conn.execute("BEGIN IMMEDIATE")
    seed_defaults(conn)
    conn.execute("COMMIT")


def _has_tables(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users_profile'"
    ).fetchone()
    return row is not None
