"""Reads and writes of the single user profile row."""

import sqlite3

from .models import DEFAULT_USER_ID


def get_cash_balance(conn: sqlite3.Connection) -> float:
    """Available cash."""
    row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
    ).fetchone()
    return row["cash_balance"]


def set_cash_balance(conn: sqlite3.Connection, amount: float) -> None:
    """Overwrite the cash balance with an already-computed amount."""
    conn.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?", (amount, DEFAULT_USER_ID)
    )
