"""Persistence for FinAlly.

Open a unit of work with `transaction()` and pass the connection it yields to
the repository functions:

    from app.db import positions, profile, transaction

    with transaction() as conn:
        profile.set_cash_balance(conn, 9500.0)
        positions.upsert(conn, "AAPL", 10.0, 190.0)

Everything in the block commits together or not at all. The schema is created
and seeded on first use, so no migration step exists.
"""

from . import chat, positions, profile, snapshots, trades, watchlist
from .connection import connect, database_path, initialize, transaction
from .models import ChatMessage, Position, Snapshot, Trade, WatchlistEntry
from .seed import DEFAULT_TICKERS, STARTING_CASH

__all__ = [
    "DEFAULT_TICKERS",
    "STARTING_CASH",
    "ChatMessage",
    "Position",
    "Snapshot",
    "Trade",
    "WatchlistEntry",
    "chat",
    "connect",
    "database_path",
    "initialize",
    "positions",
    "profile",
    "snapshots",
    "trades",
    "transaction",
    "watchlist",
]
