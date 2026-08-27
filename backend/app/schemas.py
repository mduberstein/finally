from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TradeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    quantity: float = Field(gt=0)
    side: str = Field(pattern="^(buy|sell)$")


class TradeAction(BaseModel):
    ticker: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)


class WatchlistChange(BaseModel):
    ticker: str
    action: str = Field(pattern="^(add|remove)$")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatStructuredResponse(BaseModel):
    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)


class TradeRow(BaseModel):
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


class PositionRow(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class PortfolioResponse(BaseModel):
    user_id: str
    cash_balance: float
    total_value: float
    total_unrealized_pnl: float
    positions: list[PositionRow]
    timestamp: str


class WatchlistItem(BaseModel):
    ticker: str
    price: float
    previous_price: float
    timestamp: float
    change: float
    change_percent: float
    direction: str


class ChatActionResult(BaseModel):
    type: str
    detail: str


class ChatResponse(BaseModel):
    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)
    executed_actions: list[ChatActionResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    data_initialized: bool


def success_payload(message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ok": True, "message": message, **(data or {})}
