"""SSE endpoint streaming price updates from the shared `PriceCache`."""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from .cache import PriceCache
from .models import PriceUpdate

STREAM_INTERVAL = 0.5


async def price_events(cache: PriceCache) -> AsyncIterator[dict]:
    """Yield SSE frames: a full snapshot first, then changes only."""
    seen: dict[str, float] = {}

    for update in cache.snapshot():
        seen[update.ticker] = update.price
        yield _format(update)

    while True:
        await asyncio.sleep(STREAM_INTERVAL)
        for update in cache.snapshot():
            if seen.get(update.ticker) != update.price:
                seen[update.ticker] = update.price
                yield _format(update)


def _format(update: PriceUpdate) -> dict:
    # `data` is explicitly JSON-encoded rather than left as a nested dict:
    # sse-starlette falls back to `str(data)` for non-string payloads, which
    # produces a Python repr (single-quoted) that `JSON.parse` on the
    # frontend cannot read.
    payload = {
        "ticker": update.ticker,
        "price": update.price,
        "previous_price": update.previous_price,
        "change": update.change,
        "change_percent": round(update.change_percent, 4),
        "direction": update.direction,
        "timestamp": update.timestamp.isoformat(),
    }
    return {"event": "price", "data": json.dumps(payload)}


def create_stream_router(cache: PriceCache) -> APIRouter:
    """Build the `/api/stream/prices` router bound to a specific cache.

    A factory (rather than a module-level router reading `request.app.state`)
    keeps this endpoint independently testable without a full app lifespan.
    """
    router = APIRouter()

    @router.get("/api/stream/prices")
    async def stream_prices(request: Request) -> EventSourceResponse:
        return EventSourceResponse(price_events(cache))

    return router
