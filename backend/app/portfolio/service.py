"""HTTP-agnostic trade execution and portfolio snapshot computation.

Both `execute_trade` and `get_portfolio` are plain functions with no FastAPI
dependency, so Phase 4's chat flow can import and call them directly rather
than re-implementing trade validation.
"""

import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime

from app.db.database import DEFAULT_USER_ID, connect, db_path
from app.market.cache import PriceCache

from .models import InsufficientCashError, TradeResult, UntradableTickerError


def execute_trade(ticker: str, side: str, quantity: float, cache: PriceCache) -> TradeResult:
    """Fill a trade at the current cached price and commit it atomically.

    `quantity` is typed `float` at this layer even though this phase's
    endpoint constrains it to a positive integer — Phase 4 adds fractional
    LLM-initiated trades and should not need a signature change.
    """
    ticker = ticker.upper()
    update = cache.get(ticker)
    if update is None:
        raise UntradableTickerError(ticker)
    price = update.price

    with closing(sqlite3.connect(db_path(), isolation_level=None)) as conn:
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            cash_balance = _read_cash_balance(conn)
            position = _read_position(conn, ticker)
            cost = quantity * price

            if side == "buy":
                if cost > cash_balance:
                    raise InsufficientCashError(ticker, cost, cash_balance)
                new_cash_balance = cash_balance - cost
                _apply_buy(conn, ticker, quantity, price, position)
            else:
                raise ValueError(f"unsupported trade side: {side!r}")

            executed_at = datetime.now(UTC).isoformat()
            _insert_trade(conn, ticker, side, quantity, price, executed_at)
            _write_cash_balance(conn, new_cash_balance)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    return TradeResult(
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        executed_at=executed_at,
        cash_balance=new_cash_balance,
    )


def get_portfolio(cache: PriceCache) -> dict:
    """Read-only snapshot: cash, positions with live P&L, and totals."""
    with closing(connect()) as conn:
        cash_balance = _read_cash_balance(conn)
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?",
            (DEFAULT_USER_ID,),
        ).fetchall()

    positions = []
    positions_value = 0.0
    for row in rows:
        entry = _position_entry(row, cache)
        if entry["price"] is not None:
            positions_value += entry["quantity"] * entry["price"]
        positions.append(entry)

    return {
        "cash_balance": cash_balance,
        "positions_value": positions_value,
        "total_value": cash_balance + positions_value,
        "positions": positions,
    }


def _position_entry(row: sqlite3.Row, cache: PriceCache) -> dict:
    update = cache.get(row["ticker"])
    price = update.price if update is not None else None
    unrealized_pnl = None
    change_percent = None
    if price is not None:
        unrealized_pnl = row["quantity"] * (price - row["avg_cost"])
        if row["avg_cost"] != 0:
            change_percent = round((price - row["avg_cost"]) / row["avg_cost"] * 100, 4)
    return {
        "ticker": row["ticker"],
        "quantity": row["quantity"],
        "avg_cost": row["avg_cost"],
        "price": price,
        "unrealized_pnl": unrealized_pnl,
        "change_percent": change_percent,
    }


def _read_cash_balance(conn: sqlite3.Connection) -> float:
    row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?",
        (DEFAULT_USER_ID,),
    ).fetchone()
    return row["cash_balance"]


def _write_cash_balance(conn: sqlite3.Connection, cash_balance: float) -> None:
    conn.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
        (cash_balance, DEFAULT_USER_ID),
    )


def _read_position(conn: sqlite3.Connection, ticker: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
        (DEFAULT_USER_ID, ticker),
    ).fetchone()


def _apply_buy(
    conn: sqlite3.Connection,
    ticker: str,
    quantity: float,
    price: float,
    position: sqlite3.Row | None,
) -> None:
    now = datetime.now(UTC).isoformat()
    cost = quantity * price
    if position is None:
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, DEFAULT_USER_ID, ticker, quantity, price, now),
        )
        return

    new_quantity = position["quantity"] + quantity
    new_avg_cost = ((position["quantity"] * position["avg_cost"]) + cost) / new_quantity
    conn.execute(
        "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? WHERE id = ?",
        (new_quantity, new_avg_cost, now, position["id"]),
    )


def _insert_trade(
    conn: sqlite3.Connection,
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    executed_at: str,
) -> None:
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uuid.uuid4().hex, DEFAULT_USER_ID, ticker, side, quantity, price, executed_at),
    )
