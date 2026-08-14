"""SQLite persistence: lazy schema init, additive seeding, watchlist reads."""

from .database import DEFAULT_TICKERS, DEFAULT_USER_ID, connect, initialize, watchlist_tickers

__all__ = [
    "DEFAULT_TICKERS",
    "DEFAULT_USER_ID",
    "connect",
    "initialize",
    "watchlist_tickers",
]
