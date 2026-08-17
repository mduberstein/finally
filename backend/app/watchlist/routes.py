"""Watchlist router: owns the whole `/api/watchlist` HTTP surface."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app import db
from app.market.cache import PriceCache
from app.market.models import PriceUpdate

from .models import WatchlistRejected
from .service import add_ticker, remove_ticker


class WatchlistAddRequest(BaseModel):
    """The add request body. No id, no timestamp, no price -- the server
    owns all three."""

    ticker: str


def create_watchlist_router(cache: PriceCache) -> APIRouter:
    """Build the watchlist router bound to a specific cache.

    A factory (rather than a module-level router reading `request.app.state`)
    keeps these endpoints independently testable without a full app
    lifespan, matching `create_portfolio_router`.
    """
    router = APIRouter()

    @router.get("/api/watchlist")
    async def watchlist() -> list[dict]:
        tickers = await run_in_threadpool(db.watchlist_tickers)
        return [_watchlist_entry(ticker, cache.get(ticker)) for ticker in tickers]

    @router.post("/api/watchlist")
    async def add_watchlist_ticker(request: WatchlistAddRequest) -> dict:
        try:
            normalized = await run_in_threadpool(add_ticker, request.ticker)
        except WatchlistRejected as error:
            raise HTTPException(status_code=400, detail=error.detail()) from error
        return _watchlist_entry(normalized, cache.get(normalized))

    @router.delete("/api/watchlist/{ticker}")
    async def delete_watchlist_ticker(ticker: str) -> dict:
        try:
            removed = await run_in_threadpool(remove_ticker, ticker)
        except WatchlistRejected as error:
            raise HTTPException(status_code=400, detail=error.detail()) from error
        return {"ticker": ticker.strip().upper(), "removed": removed}

    return router


def _watchlist_entry(ticker: str, update: PriceUpdate | None) -> dict:
    if update is None:
        return {
            "ticker": ticker,
            "price": None,
            "previous_price": None,
            "change": None,
            "change_percent": None,
            "direction": None,
            "timestamp": None,
        }
    return {
        "ticker": ticker,
        "price": update.price,
        "previous_price": update.previous_price,
        "change": update.change,
        "change_percent": round(update.change_percent, 4),
        "direction": update.direction,
        "timestamp": update.timestamp.isoformat(),
    }
