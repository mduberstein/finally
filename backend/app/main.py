"""The FastAPI application: one price cache, one market feed, one snapshot task."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from app.api import (
    create_chat_router,
    create_portfolio_router,
    create_watchlist_router,
    health_router,
)
from app.db import connect, initialize, watchlist
from app.market import MarketFeed, PriceCache, create_source
from app.market.simulator import SimulatorSource
from app.market.stream import create_stream_router
from app.portfolio import SnapshotRecorder, TradeError

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent / "static"
"""Where the Dockerfile copies the Next.js static export."""


def create_app(cache: PriceCache | None = None) -> FastAPI:
    """Build the application. Pass a cache to drive it with known prices in tests."""
    prices = cache or PriceCache()
    app = FastAPI(title="FinAlly", lifespan=_lifespan(prices))
    app.state.prices = prices
    app.add_exception_handler(TradeError, _trade_error_response)

    app.include_router(health_router)
    app.include_router(create_portfolio_router(prices))
    app.include_router(create_watchlist_router(prices))
    app.include_router(create_chat_router(prices))
    app.include_router(create_stream_router(prices))
    _mount_static(app)
    return app


def _lifespan(cache: PriceCache):
    """One feed and one snapshot task for the process lifetime."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        initialize()
        feed = MarketFeed(
            create_source(),
            cache,
            watched_tickers,
            fallback_factory=SimulatorSource,
        )
        recorder = SnapshotRecorder(cache)
        feed.start()
        recorder.start()
        try:
            yield
        finally:
            await recorder.stop()
            await feed.stop()

    return lifespan


def watched_tickers() -> list[str]:
    """The tickers the feed should poll, re-read on every poll.

    Assumes `initialize()` has run, which the lifespan handler does before
    starting the feed.

    Uses a plain connection rather than `transaction()`: the feed calls this on
    the event loop, and `transaction()` opens with BEGIN IMMEDIATE, which would
    wait behind a concurrent trade's write lock. A WAL read never blocks against
    a writer. The connection is opened and closed per call, never cached -- a
    long-lived reader pins the WAL and stops it checkpointing, and with the
    simulator this runs twice a second.
    """
    conn = connect()
    try:
        return [entry.ticker for entry in watchlist.list_all(conn)]
    finally:
        conn.close()


def _trade_error_response(request: Request, exc: TradeError) -> JSONResponse:
    """A broken trading rule is a 400 carrying the message the LLM reads back."""
    return JSONResponse(status_code=400, content={"detail": exc.detail})


class _SinglePageFiles(StaticFiles):
    """The static export, serving `index.html` for anything that is not a file.

    The frontend is a single route, so `/` and any deep link or reload must
    return the same HTML shell. `/api` is deliberately excluded: an unknown API
    path stays a JSON 404 instead of quietly returning HTML, which would turn a
    typo'd endpoint into a confusing frontend bug.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or scope["path"].startswith("/api"):
                raise
            return await super().get_response("index.html", scope)


def _mount_static(app: FastAPI) -> None:
    """Serve the built frontend from every path the API did not claim.

    Mounted after the routers because Starlette matches in registration order,
    so a registered `/api/*` route always wins. The directory is absent during
    backend-only local development, and the app starts and serves the API alone.
    """
    if not STATIC_DIR.is_dir():
        logger.info("no static export at %s; serving the API only", STATIC_DIR)
        return
    app.mount("/", _SinglePageFiles(directory=STATIC_DIR), name="static")


app = create_app()
