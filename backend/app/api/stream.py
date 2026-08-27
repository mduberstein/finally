from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/stream", tags=["streaming"])


@router.get("/prices")
async def stream_prices(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _generate_events(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _generate_events(request: Request, interval: float = 0.5) -> AsyncGenerator[str, None]:
    yield "retry: 1000\n\n"
    cache = request.app.state._finally.price_cache
    last_version = -1
    while True:
        if await request.is_disconnected():
            break
        version = cache.version
        if version != last_version:
            last_version = version
            payload = cache.get_all()
            if payload:
                data = json.dumps({ticker: update.to_dict() for ticker, update in payload.items()})
                yield f"data: {data}\n\n"
        await asyncio.sleep(interval)
