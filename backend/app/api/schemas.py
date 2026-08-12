"""Request and response bodies, exactly as API_CONTRACT.md specifies them."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TICKER_PATTERN = r"^[A-Za-z]{1,5}$"


class _FromObject(BaseModel):
    """Base for responses built straight from the service layer's dataclasses."""

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str


class PositionOut(_FromObject):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    weight: float


class PortfolioResponse(_FromObject):
    cash_balance: float
    positions_value: float
    total_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: float
    positions: list[PositionOut]


class TradeRequest(BaseModel):
    ticker: str = Field(pattern=TICKER_PATTERN)
    quantity: float = Field(gt=0)
    side: Literal["buy", "sell"]


class TradeOut(_FromObject):
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


class TradeResponse(_FromObject):
    trade: TradeOut
    cash_balance: float
    position: PositionOut | None


class SnapshotOut(_FromObject):
    total_value: float
    recorded_at: str


class HistoryResponse(BaseModel):
    snapshots: list[SnapshotOut]


class WatchlistItemOut(BaseModel):
    """A watched ticker with its latest price, or nulls until the feed sees it."""

    ticker: str
    added_at: str
    price: float | None
    previous_price: float | None
    change: float | None
    change_percent: float | None
    direction: str | None


class WatchlistResponse(BaseModel):
    tickers: list[WatchlistItemOut]


class WatchlistRequest(BaseModel):
    ticker: str = Field(pattern=TICKER_PATTERN)
