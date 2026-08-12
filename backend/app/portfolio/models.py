"""Valued views of the portfolio, shaped exactly as API_CONTRACT.md serializes them."""

from dataclasses import dataclass

from app.db import Trade


@dataclass(frozen=True, slots=True)
class PositionView:
    """One holding priced against the live cache."""

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    weight: float


@dataclass(frozen=True, slots=True)
class PortfolioView:
    """Cash, holdings, and the totals derived from both."""

    cash_balance: float
    positions_value: float
    total_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: float
    positions: list[PositionView]

    def position(self, ticker: str) -> PositionView | None:
        """The valued holding in one ticker, or None if it is not held."""
        return next((p for p in self.positions if p.ticker == ticker), None)


@dataclass(frozen=True, slots=True)
class TradeResult:
    """What an executed trade changed. `position` is None when a sell closed it."""

    trade: Trade
    cash_balance: float
    position: PositionView | None
