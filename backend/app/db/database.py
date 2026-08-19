"""Lazy SQLite initialization, additive seeding, and watchlist reads.

Contract: `initialize()` is purely additive — it never removes a table, empties
a table, or discards a row. Every CREATE is `IF NOT EXISTS`; every seed
INSERT is `OR IGNORE`.
Calling `initialize()` against an existing, fully-seeded database is a no-op;
calling it against a database missing some tables adds exactly the missing
ones, leaving existing rows untouched. `initialize()` also emits one startup
log record naming the resolved absolute database path and whether a file
already existed there — an operator's evidence that persistence is (or is
not) actually wired to the intended bind mount.
"""

import logging
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

# Routed through "uvicorn.error" rather than a plain module logger: uvicorn's
# default dictConfig only attaches handlers to the uvicorn.* loggers, leaving
# the root logger bare, so a `logging.getLogger(__name__).info(...)` call
# here would fall through to `logging.lastResort` and never reach `docker
# logs` (lastResort only emits WARNING and above). Every existing call site
# in this codebase logs at warning/error/exception, which is why none of
# them hit this. This line is the entire mitigation for a misconfigured or
# absent bind mount silently degrading into data loss — it must be visible.
logger = logging.getLogger("uvicorn.error")

DEFAULT_USER_ID = "default"

DEFAULT_TICKERS: tuple[str, ...] = (
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
)

DEFAULT_CASH_BALANCE = 10000.0

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def db_path() -> Path:
    """Resolve the SQLite file path.

    Reads `FINALLY_DB_PATH`, defaulting to `db/finally.db` resolved against
    the repository root (the parent of the `backend` directory), matching
    the Docker volume mount target in planning/PLAN.md section 11.
    """
    override = os.getenv("FINALLY_DB_PATH")
    if override:
        return Path(override)
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "db" / "finally.db"


def connect() -> sqlite3.Connection:
    """Open a new short-lived connection with row access by column name.

    A fresh connection per call keeps this free of cross-task state; local
    SQLite reads are microseconds, and the feed's 2 Hz poll is not a load
    concern.
    """
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize() -> None:
    """Create the schema and seed default data, additively.

    Creates the parent directory if needed, runs the full schema script
    (all CREATE TABLE IF NOT EXISTS), then seeds the default user profile
    and the ten default watchlist tickers, both via INSERT OR IGNORE.
    """
    path = db_path()
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)

    with closing(connect()) as conn, conn:
        conn.executescript(_SCHEMA_PATH.read_text())
        _seed_user_profile(conn)
        _seed_watchlist(conn)

    if existed:
        logger.info("Opened existing database at %s", path)
    else:
        logger.info("Created and seeded a new database at %s", path)


def _seed_user_profile(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, _now_iso()),
    )


def _seed_watchlist(conn: sqlite3.Connection) -> None:
    for ticker in DEFAULT_TICKERS:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (uuid.uuid4().hex, DEFAULT_USER_ID, ticker, _now_iso()),
        )


def watchlist_tickers() -> list[str]:
    """Tickers on the default user's watchlist, in add order.

    This is the callable handed to `MarketFeed` — it is re-read on every
    poll so watchlist changes take effect without restarting the feed.
    """
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY rowid",
            (DEFAULT_USER_ID,),
        ).fetchall()
    return [row["ticker"] for row in rows]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
