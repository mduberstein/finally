"""Market-order execution: validate, move cash and shares, log, snapshot."""

import sqlite3

from app.db import Position, positions, profile, snapshots, trades, transaction
from app.market import PriceCache

from .errors import TradeError
from .models import TradeResult
from .valuation import build_portfolio

EPSILON = 1e-9
"""Tolerance on cash and share comparisons.

A position quantity is the running sum of fractional buys, so it is inexact by
construction: 0.1 + 0.2 stores as 0.30000000000000004. Without this a user
selling the exact quantity the UI shows them would be told they do not hold it.
"""


def execute_trade(cache: PriceCache, ticker: str, side: str, quantity: float) -> TradeResult:
    """Fill a market order instantly at the current cached price, no fees.

    Cash, position, trade log, and snapshot all move inside one transaction, so
    a trade can never debit cash without recording where the money went.
    Synchronous by design: `sqlite3` is, and the writes take microseconds. Call
    it from a `def` route handler, or via `run_in_threadpool` from an async one,
    so it never blocks the loop serving SSE connections.
    """
    ticker = ticker.upper()
    price = _price_for(cache, ticker)

    with transaction() as conn:
        cash = profile.get_cash_balance(conn)
        existing = positions.get(conn, ticker)

        if side == "buy":
            new_cash, holding = _buy(ticker, quantity, price, cash, existing)
        else:
            new_cash, holding = _sell(ticker, quantity, price, cash, existing)

        profile.set_cash_balance(conn, new_cash)
        _store(conn, ticker, holding)
        trade = trades.append(conn, ticker, side, quantity, price)

        portfolio = build_portfolio(conn, cache)
        snapshots.append(conn, portfolio.total_value)

    return TradeResult(
        trade=trade,
        cash_balance=portfolio.cash_balance,
        position=portfolio.position(ticker),
    )


def _price_for(cache: PriceCache, ticker: str) -> float:
    update = cache.get(ticker)
    if update is None:
        raise TradeError(f"No price available for {ticker}")
    return update.price


def _buy(
    ticker: str, quantity: float, price: float, cash: float, existing: Position | None
) -> tuple[float, tuple[float, float]]:
    """Debit cash and fold the fill into a recomputed weighted average cost."""
    cost = price * quantity
    if cost > cash + EPSILON:
        raise TradeError(f"Insufficient cash: need ${cost:.2f}, have ${cash:.2f}")

    held = existing.quantity if existing else 0.0
    basis = existing.quantity * existing.avg_cost if existing else 0.0
    total_quantity = held + quantity
    return cash - cost, (total_quantity, (basis + cost) / total_quantity)


def _sell(
    ticker: str, quantity: float, price: float, cash: float, existing: Position | None
) -> tuple[float, tuple[float, float] | None]:
    """Credit cash and reduce the holding. `avg_cost` is unchanged by a sell."""
    held = existing.quantity if existing else 0.0
    if quantity > held + EPSILON:
        raise TradeError(
            f"Insufficient shares: tried to sell {_amount(quantity)} {ticker}, hold {_amount(held)}"
        )

    remaining = held - quantity
    if remaining <= EPSILON:
        return cash + price * quantity, None
    return cash + price * quantity, (remaining, existing.avg_cost)


def _store(conn: sqlite3.Connection, ticker: str, holding: tuple[float, float] | None) -> None:
    if holding is None:
        positions.delete(conn, ticker)
    else:
        positions.upsert(conn, ticker, holding[0], holding[1])


def _amount(quantity: float) -> str:
    """Share counts in error messages read as "10" and "0.5", never "10.0"."""
    return f"{quantity:g}"
