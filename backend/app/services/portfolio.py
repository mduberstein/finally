from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.config import APP_USER_ID
from app.db import Database
from app.market import PriceCache


@dataclass(frozen=True)
class PortfolioPosition:
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


def _safe_div(num: float, denom: float) -> float:
    if denom == 0:
        return 0.0
    return num / denom


def list_portfolio_with_market_data(database: Database, price_cache: PriceCache) -> dict[str, Any]:
    profile = database.get_profile()
    positions = database.list_positions()
    output_positions: list[PortfolioPosition] = []

    total_unrealized = 0.0
    total_invested = 0.0
    total_value = float(profile["cash_balance"])

    for position in positions:
        current = price_cache.get_price(position.ticker) or 0.0
        market_value = current * position.quantity
        cost = position.avg_cost * position.quantity
        unrealized = market_value - cost
        unrealized_pct = _safe_div(unrealized, cost) * 100 if position.quantity else 0.0
        total_unrealized += unrealized
        total_invested += cost
        total_value += market_value

        output_positions.append(
            PortfolioPosition(
                ticker=position.ticker,
                quantity=position.quantity,
                avg_cost=position.avg_cost,
                current_price=current,
                unrealized_pnl=round(unrealized, 4),
                unrealized_pnl_pct=round(unrealized_pct, 4),
            )
        )

    if total_invested < 0:
        total_unrealized = total_unrealized  # pragma: no cover

    return {
        "user_id": APP_USER_ID,
        "cash_balance": round(float(profile["cash_balance"]), 2),
        "total_value": round(total_value, 2),
        "total_unrealized_pnl": round(total_unrealized, 4),
        "positions": output_positions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def execute_trade(database: Database, price_cache: PriceCache, ticker: str, side: str, quantity: float) -> dict[str, Any]:
    normalized_ticker = ticker.upper().strip()
    price = price_cache.get_price(normalized_ticker)
    if price is None:
        raise ValueError(f"Price unavailable for {normalized_ticker}")
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"Invalid price for {normalized_ticker}")

    return database.execute_market_order(normalized_ticker, side, quantity, float(price))
