"""The set of tickers the user is watching."""

import sqlite3

from .models import DEFAULT_USER_ID, WatchlistEntry, new_id, utc_now


def list_all(conn: sqlite3.Connection) -> list[WatchlistEntry]:
    """Every watched ticker, oldest addition first."""
    rows = conn.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid",
        (DEFAULT_USER_ID,),
    ).fetchall()
    return [_entry(row) for row in rows]


def add(conn: sqlite3.Connection, ticker: str) -> WatchlistEntry:
    """Add a ticker. Raises sqlite3.IntegrityError if it is already watched."""
    entry = WatchlistEntry(ticker=ticker, added_at=utc_now())
    conn.execute(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        (new_id(), DEFAULT_USER_ID, entry.ticker, entry.added_at),
    )
    return entry


def remove(conn: sqlite3.Connection, ticker: str) -> bool:
    """Remove a ticker, returning whether it was there to remove."""
    cursor = conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (DEFAULT_USER_ID, ticker)
    )
    return cursor.rowcount > 0


def exists(conn: sqlite3.Connection, ticker: str) -> bool:
    """Whether the ticker is already watched."""
    row = conn.execute(
        "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?", (DEFAULT_USER_ID, ticker)
    ).fetchone()
    return row is not None


def _entry(row: sqlite3.Row) -> WatchlistEntry:
    return WatchlistEntry(ticker=row["ticker"], added_at=row["added_at"])
