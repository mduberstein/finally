"""Default rows written when the database is first created."""

import sqlite3

from .models import DEFAULT_USER_ID, new_id, utc_now

STARTING_CASH = 10000.0

DEFAULT_TICKERS = (
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


def seed_defaults(conn: sqlite3.Connection) -> None:
    """Insert the default profile and watchlist, leaving any existing rows alone."""
    now = utc_now()
    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, STARTING_CASH, now),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        [(new_id(), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_TICKERS],
    )
