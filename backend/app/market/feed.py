import asyncio
import logging
from collections.abc import Callable, Sequence

import httpx

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)

MAX_BACKOFF_SECONDS = 60.0
PERMANENT_FAILURE_STATUSES = frozenset({401, 403})
RATE_LIMIT_STATUS = 429


class MarketFeed:
    """Background task polling a source and writing into the cache.

    On a permanent auth/plan failure (401/403) the feed swaps to
    ``fallback_factory()`` if one was supplied, so a misconfigured or
    downgraded API key degrades to a working demo instead of a blank UI.
    A 429 doubles the poll interval up to ``MAX_BACKOFF_SECONDS``; any other
    error (5xx, timeouts, network faults) just retries next tick at the
    source's normal interval, serving stale cached prices in the meantime.
    """

    def __init__(
        self,
        source: MarketDataSource,
        cache: PriceCache,
        tickers: Callable[[], Sequence[str]],
        fallback_factory: Callable[[], MarketDataSource] | None = None,
    ) -> None:
        self._source = source
        self._cache = cache
        self._tickers = tickers
        self._fallback_factory = fallback_factory
        self._task: asyncio.Task | None = None
        self._backoff_interval: float | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

async def stop(self) -> None:
    if self._task:
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
    await self._source.aclose()
    async def _run(self) -> None:
        while True:
            try:
                quotes = await self._source.fetch(self._tickers())
                self._cache.apply(quotes)
                self._backoff_interval = None
            except asyncio.CancelledError:
                raise
            except httpx.HTTPStatusError as exc:
                await self._handle_http_error(exc)
            except Exception:
                logger.exception("market fetch failed, serving cached prices")
            await asyncio.sleep(self._backoff_interval or self._source.poll_interval)

    async def _handle_http_error(self, exc: httpx.HTTPStatusError) -> None:
        status = exc.response.status_code
        if status in PERMANENT_FAILURE_STATUSES:
            logger.error(
                "market data source %r rejected (HTTP %s); falling back",
                self._source.name,
                status,
            )
            if self._fallback_factory is not None:
                await self._source.aclose()
                self._source = self._fallback_factory()
                self._backoff_interval = None
        elif status == RATE_LIMIT_STATUS:
            base = self._backoff_interval or self._source.poll_interval
            self._backoff_interval = min(base * 2, MAX_BACKOFF_SECONDS)
            logger.warning(
                "market data source %r rate limited; backing off to %.1fs",
                self._source.name,
                self._backoff_interval,
            )
        else:
            logger.exception("market fetch failed, serving cached prices")
