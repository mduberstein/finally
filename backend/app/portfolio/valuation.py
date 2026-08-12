"""Pricing held positions against the shared cache and deriving P&L."""

import sqlite3

from app.db import Position, positions, profile, transaction
from app.market import PriceCache

from .models import PortfolioView, PositionView


def load_portfolio(cache: PriceCache) -> PortfolioView:
    """The current portfolio, read in its own transaction.

    Synchronous, like everything touching `sqlite3`. See `execute_trade` for
    why that is deliberate and how to call it from async code.
    """
    with transaction() as conn:
        return build_portfolio(conn, cache)


def build_portfolio(conn: sqlite3.Connection, cache: PriceCache) -> PortfolioView:
    """Value every holding at its cached price and total the account.

    Takes an open connection so a trade can value the portfolio it just wrote
    inside the same transaction, before anything is visible to other readers.
    """
    cash = profile.get_cash_balance(conn)
    held = positions.list_all(conn)
    priced = [(position, current_price(cache, position)) for position in held]

    positions_value = sum(position.quantity * price for position, price in priced)
    cost_basis = sum(position.quantity * position.avg_cost for position, price in priced)
    total = cash + positions_value
    pnl = positions_value - cost_basis

    return PortfolioView(
        cash_balance=_money(cash),
        positions_value=_money(positions_value),
        total_value=_money(total),
        total_unrealized_pnl=_money(pnl),
        total_unrealized_pnl_percent=_percent(_ratio(pnl, cost_basis) * 100),
        positions=[_view(position, price, total) for position, price in priced],
    )


def current_price(cache: PriceCache, position: Position) -> float:
    """The cached price, falling back to cost so a fresh ticker never prices as null."""
    update = cache.get(position.ticker)
    return update.price if update else position.avg_cost


def _view(position: Position, price: float, total_value: float) -> PositionView:
    market_value = position.quantity * price
    pnl = market_value - position.quantity * position.avg_cost
    return PositionView(
        ticker=position.ticker,
        quantity=position.quantity,
        avg_cost=_money(position.avg_cost),
        current_price=_money(price),
        market_value=_money(market_value),
        unrealized_pnl=_money(pnl),
        unrealized_pnl_percent=_percent(_ratio(price - position.avg_cost, position.avg_cost) * 100),
        weight=round(_ratio(market_value, total_value), 4),
    )


def _ratio(numerator: float, denominator: float) -> float:
    """Guard the empty-portfolio and zero-cost cases, which are 0% rather than undefined."""
    return numerator / denominator if denominator else 0.0


def _money(value: float) -> float:
    return round(value, 2)


def _percent(value: float) -> float:
    return round(value, 2)
