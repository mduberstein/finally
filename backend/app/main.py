"""FastAPI application: lifespan wiring, REST routes, and static file serving."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app import db
from app.market import MarketFeed, PriceCache, PriceUpdate, create_source
from app.market.simulator import SimulatorSource
from app.market.stream import create_stream_router
from app.portfolio import create_portfolio_router

# Module-level cache: the stream router factory binds to a cache at import
# time, so it must exist before the app object (and its lifespan) is built.
cache = PriceCache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.initialize()
    feed = MarketFeed(
        create_source(),
        cache,
        db.watchlist_tickers,
        fallback_factory=SimulatorSource,
    )
    feed.start()
    app.state.prices = cache
    app.state.feed = feed
    yield
    await feed.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/watchlist")
async def watchlist() -> list[dict]:
    tickers = await run_in_threadpool(db.watchlist_tickers)
    return [_watchlist_entry(ticker, cache.get(ticker)) for ticker in tickers]


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


app.include_router(create_stream_router(cache))
app.include_router(create_portfolio_router(cache))

# Resolved against the repo root (not the process cwd) so `backend/static`
# means the same directory whether uvicorn is started from the repo root or
# from inside `backend/`.
_repo_root = Path(__file__).resolve().parents[2]
_static_dir = Path(os.getenv("FINALLY_STATIC_DIR", str(_repo_root / "backend" / "static")))
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
