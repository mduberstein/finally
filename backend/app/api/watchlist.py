"""Watchlist CRUD. Prices come from the shared cache, null until the feed sees a ticker."""

from fastapi import APIRouter, HTTPException

from app.db import WatchlistEntry, transaction, watchlist
from app.market import PriceCache

from .schemas import WatchlistItemOut, WatchlistRequest, WatchlistResponse


def create_watchlist_router(cache: PriceCache) -> APIRouter:
    """Build the `/api/watchlist` router bound to a specific price cache.

    Handlers are plain `def` for the reason documented in `portfolio.py`.
    """
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("", response_model=WatchlistResponse)
    def get_watchlist() -> WatchlistResponse:
        with transaction() as conn:
            entries = watchlist.list_all(conn)
        return WatchlistResponse(tickers=[_item(entry, cache) for entry in entries])

    @router.post("", response_model=WatchlistItemOut, status_code=201)
    def add_ticker(body: WatchlistRequest) -> WatchlistItemOut:
        ticker = body.ticker.upper()
        with transaction() as conn:
            if watchlist.exists(conn, ticker):
                raise HTTPException(409, f"{ticker} is already on the watchlist")
            entry = watchlist.add(conn, ticker)
        return _item(entry, cache)

    @router.delete("/{ticker}", status_code=204)
    def remove_ticker(ticker: str) -> None:
        """Stop watching a ticker. Any position in it is deliberately left open."""
        symbol = ticker.upper()
        with transaction() as conn:
            if not watchlist.remove(conn, symbol):
                raise HTTPException(404, f"{symbol} is not on the watchlist")

    return router


def _item(entry: WatchlistEntry, cache: PriceCache) -> WatchlistItemOut:
    update = cache.get(entry.ticker)
    if update is None:
        return WatchlistItemOut(
            ticker=entry.ticker,
            added_at=entry.added_at,
            price=None,
            previous_price=None,
            change=None,
            change_percent=None,
            direction=None,
        )
    return WatchlistItemOut(
        ticker=entry.ticker,
        added_at=entry.added_at,
        price=update.price,
        previous_price=update.previous_price,
        change=update.change,
        change_percent=round(update.change_percent, 4),
        direction=update.direction,
    )
