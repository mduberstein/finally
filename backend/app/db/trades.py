"""The append-only trade log."""

import sqlite3

from .models import DEFAULT_USER_ID, Trade, new_id, utc_now


def append(
    conn: sqlite3.Connection, ticker: str, side: str, quantity: float, price: float
) -> Trade:
    """Record an executed trade. `side` is "buy" or "sell"."""
    trade = Trade(
        id=new_id(),
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        executed_at=utc_now(),
    )
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            trade.id,
            DEFAULT_USER_ID,
            trade.ticker,
            trade.side,
            trade.quantity,
            trade.price,
            trade.executed_at,
        ),
    )
    return trade


def list_recent(conn: sqlite3.Connection, limit: int = 50) -> list[Trade]:
    """The most recent trades, newest first."""
    rows = conn.execute(
        "SELECT id, ticker, side, quantity, price, executed_at FROM trades"
        " WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?",
        (DEFAULT_USER_ID, limit),
    ).fetchall()
    return [_trade(row) for row in rows]


def _trade(row: sqlite3.Row) -> Trade:
    return Trade(
        id=row["id"],
        ticker=row["ticker"],
        side=row["side"],
        quantity=row["quantity"],
        price=row["price"],
        executed_at=row["executed_at"],
    )
