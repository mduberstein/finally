"""HTTP-agnostic watchlist add and remove over the watchlist table.

Plain functions with no FastAPI dependency, so Phase 4's chat flow can import
and call them directly rather than re-implementing validation -- the same
rule `app/portfolio/service.py` documents for `execute_trade`.
"""

import re
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime

from app.db.database import DEFAULT_USER_ID, connect, db_path

from .models import DuplicateTickerError, InvalidTickerError, WatchlistFullError

MAX_WATCHLIST_TICKERS = 50

_TICKER_PATTERN = re.compile(r"^[A-Z]{1,10}$")


def normalize_ticker(ticker: str) -> str:
    """Strip, uppercase, then validate against `^[A-Z]{1,10}$`.

    Uppercasing before validation is what lets a user type lowercase.
    """
    normalized = ticker.strip().upper()
    if not _TICKER_PATTERN.match(normalized):
        raise InvalidTickerError(ticker)
    return normalized


def add_ticker(ticker: str) -> str:
    """Normalize, enforce the soft cap, and insert -- or raise a rejection.

    The count check and insert run inside one `BEGIN IMMEDIATE` transaction,
    the same pattern `execute_trade` uses to close the analogous
    cash-balance race (`app/portfolio/service.py`), so two concurrent adds
    can't both observe a stale count and push the watchlist past its cap.
    The `UNIQUE (user_id, ticker)` constraint remains the single source of
    truth for duplication within that transaction.
    """
    normalized = normalize_ticker(ticker)

    with closing(sqlite3.connect(db_path(), isolation_level=None)) as conn:
        conn.row_factory = sqlite3.Row
        began = False
        try:
            conn.execute("BEGIN IMMEDIATE")
            began = True
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM watchlist WHERE user_id = ?",
                (DEFAULT_USER_ID,),
            ).fetchone()["n"]
            if count >= MAX_WATCHLIST_TICKERS:
                raise WatchlistFullError(MAX_WATCHLIST_TICKERS)

            try:
                conn.execute(
                    "INSERT OR ABORT INTO watchlist (id, user_id, ticker, added_at) "
                    "VALUES (?, ?, ?, ?)",
                    (uuid.uuid4().hex, DEFAULT_USER_ID, normalized, datetime.now(UTC).isoformat()),
                )
            except sqlite3.IntegrityError as error:
                raise DuplicateTickerError(normalized) from error
            conn.execute("COMMIT")
        except Exception:
            if began:
                conn.execute("ROLLBACK")
            raise

    return normalized


def remove_ticker(ticker: str) -> bool:
    """Normalize then delete -- idempotent: an absent ticker is not an error.

    A retry or a double-click needs no client-side coordination. The
    statement names exactly one table; nothing in this package ever writes
    to `positions`, `trades`, `users_profile`, or `portfolio_snapshots`.
    """
    normalized = normalize_ticker(ticker)

    with closing(connect()) as conn:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (DEFAULT_USER_ID, normalized),
        )
        conn.commit()

    return cursor.rowcount > 0
