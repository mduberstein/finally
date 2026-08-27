from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.app_state import AppState, get_app_state

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)


@router.get("")
async def get_watchlist(
    state: AppState = Depends(get_app_state),
) -> list[dict[str, Any]]:
    tickers = state.database.list_watchlist()
    output: list[dict[str, Any]] = []
    for ticker in tickers:
        update = state.price_cache.get(ticker)
        if update is None:
            output.append({"ticker": ticker, "price": 0.0, "previous_price": 0.0, "timestamp": 0.0, "change": 0.0, "change_percent": 0.0, "direction": "flat"})
            continue
        output.append(update.to_dict())
    return output


@router.post("")
async def add_ticker(
    request: WatchlistRequest,
    state: AppState = Depends(get_app_state),
) -> dict[str, Any]:
    normalized = request.ticker.upper().strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid ticker")
    inserted = state.database.add_watchlist_ticker(normalized)
    if inserted:
        await state.market_data_source.add_ticker(normalized)
    return {"ok": True, "added": inserted, "ticker": normalized}


@router.delete("/{ticker}")
async def remove_ticker(
    ticker: str,
    state: AppState = Depends(get_app_state),
) -> dict[str, Any]:
    normalized = ticker.upper().strip()
    removed = state.database.remove_watchlist_ticker(normalized)
    if removed:
        await state.market_data_source.remove_ticker(normalized)
    return {"ok": True, "removed": removed, "ticker": normalized}
