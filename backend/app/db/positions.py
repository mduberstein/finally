"""Current holdings, one row per ticker."""

import sqlite3

from .models import DEFAULT_USER_ID, Position, new_id, utc_now


def list_all(conn: sqlite3.Connection) -> list[Position]:
    """Every open position, alphabetically by ticker."""
    rows = conn.execute(
        "SELECT ticker, quantity, avg_cost, updated_at FROM positions"
        " WHERE user_id = ? ORDER BY ticker",
        (DEFAULT_USER_ID,),
    ).fetchall()
    return [_position(row) for row in rows]


def get(conn: sqlite3.Connection, ticker: str) -> Position | None:
    """The position in one ticker, or None if none is held."""
    row = conn.execute(
        "SELECT ticker, quantity, avg_cost, updated_at FROM positions"
        " WHERE user_id = ? AND ticker = ?",
        (DEFAULT_USER_ID, ticker),
    ).fetchone()
    return _position(row) if row else None


def upsert(conn: sqlite3.Connection, ticker: str, quantity: float, avg_cost: float) -> Position:
    """Set the holding in a ticker, inserting or replacing the existing row."""
    position = Position(ticker=ticker, quantity=quantity, avg_cost=avg_cost, updated_at=utc_now())
    conn.execute(
        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (user_id, ticker) DO UPDATE SET"
        " quantity = excluded.quantity,"
        " avg_cost = excluded.avg_cost,"
        " updated_at = excluded.updated_at",
        (
            new_id(),
            DEFAULT_USER_ID,
            position.ticker,
            position.quantity,
            position.avg_cost,
            position.updated_at,
        ),
    )
    return position


def delete(conn: sqlite3.Connection, ticker: str) -> bool:
    """Close a position, returning whether there was one to close."""
    cursor = conn.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (DEFAULT_USER_ID, ticker)
    )
    return cursor.rowcount > 0


def _position(row: sqlite3.Row) -> Position:
    return Position(
        ticker=row["ticker"],
        quantity=row["quantity"],
        avg_cost=row["avg_cost"],
        updated_at=row["updated_at"],
    )
