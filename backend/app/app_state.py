from __future__ import annotations

import asyncio
from dataclasses import dataclass

from fastapi import Request

from app.config import DB_PATH, HISTORY_POLL_INTERVAL_SECONDS
from app.db import Database
from app.market import MarketDataSource, PriceCache, create_market_data_source
from app.services.portfolio import execute_trade as _execute_trade
from app.services.portfolio import list_portfolio_with_market_data


@dataclass
class AppState:
    database: Database
    price_cache: PriceCache
    market_data_source: MarketDataSource
    snapshot_task: asyncio.Task | None = None

    def schedule_snapshot(self, total_value: float) -> None:
        # keep simple and non-blocking: persist immediate snapshots after trades/chat actions
        try:
            self.database.append_portfolio_snapshot(total_value)
        except Exception:
            # Non-critical if snapshot fails, avoid breaking request.
            return

    def execute_trade(self, ticker: str, side: str, quantity: float) -> dict:
        result = _execute_trade(self.database, self.price_cache, ticker, side, quantity)
        portfolio = list_portfolio_with_market_data(self.database, self.price_cache)
        self.schedule_snapshot(portfolio["total_value"])
        result["portfolio_value"] = portfolio["total_value"]
        return result

    def snapshot_total_value(self) -> float:
        return list_portfolio_with_market_data(self.database, self.price_cache)["total_value"]


async def app_lifespan_state(app) -> AppState:
    database = Database(DB_PATH)
    database.initialize()
    price_cache = PriceCache()

    source = create_market_data_source(price_cache)
    tickers = database.list_watchlist()
    await source.start(tickers)

    async def snapshot_loop() -> None:
        while True:
            await asyncio.sleep(HISTORY_POLL_INTERVAL_SECONDS)
            try:
                total = list_portfolio_with_market_data(database, price_cache)["total_value"]
                database.append_portfolio_snapshot(total)
            except asyncio.CancelledError:
                raise
            except Exception:
                continue

    task = asyncio.create_task(snapshot_loop())
    app.state._finally = AppState(
        database=database,
        price_cache=price_cache,
        market_data_source=source,
        snapshot_task=task,
    )
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await source.stop()


def get_app_state(request: Request) -> AppState:
    state = request.app.state._finally
    return state
