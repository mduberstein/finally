"""Background task polling a market data source and writing into the cache."""

import asyncio
import logging
from collections.abc import Callable, Sequence

import httpx

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)

MAX_POLL_INTERVAL = 60.0
"""Ceiling for exponential backoff on HTTP 429."""

FALLBACK_STATUS_CODES = frozenset({401, 403})
"""Permanent auth/plan failures — fall back to the fallback source, not retry."""


class MarketFeed:
    """Background task polling a source and writing into the cache.

    A transient upstream failure must not kill the only task feeding the
    entire application, so any exception is logged and the loop continues
    serving stale cached prices. Two failure modes get more specific
    handling: HTTP 401/403 (permanent — wrong key or plan) trigger a
    one-time fallback to `fallback_factory`, and HTTP 429 (rate limited)
    doubles the poll interval up to `MAX_POLL_INTERVAL`.
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
        self._base_interval = source.poll_interval
        self._task: asyncio.Task | None = None

    @property
    def source(self) -> MarketDataSource:
        return self._source

    def start(self) -> None:
        """Start the background polling loop.

        Raises `RuntimeError` if already running — starting twice would
        leak the first task, which would keep polling and writing into the
        cache alongside the new one.
        """
        if self._task is not None and not self._task.done():
            raise RuntimeError("MarketFeed.start() called while already running")
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        task = self._task
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._source.aclose()

    async def _run(self) -> None:
        while True:
            await self._tick()
            await asyncio.sleep(self._source.poll_interval)

    async def _tick(self) -> None:
        """Fetch once and apply to the cache, containing any failure."""
        try:
            quotes = await self._source.fetch(self._tickers())
            self._cache.apply(quotes)
            self._source.poll_interval = self._base_interval
        except asyncio.CancelledError:
            raise
        except httpx.HTTPStatusError as exc:
            await self._handle_http_error(exc)
        except Exception:
            logger.exception("market fetch failed, serving cached prices")

    async def _handle_http_error(self, exc: httpx.HTTPStatusError) -> None:
        status = exc.response.status_code
        if status in FALLBACK_STATUS_CODES and self._fallback_factory is not None:
            logger.error(
                "market source %r rejected requests (HTTP %s); falling back",
                self._source.name,
                status,
            )
            await self._source.aclose()
            self._source = self._fallback_factory()
            self._base_interval = self._source.poll_interval
        elif status == 429:
            self._source.poll_interval = min(self._source.poll_interval * 2, MAX_POLL_INTERVAL)
            logger.warning(
                "market source %r rate limited; backing off to %.1fs",
                self._source.name,
                self._source.poll_interval,
            )
        else:
            logger.exception("market fetch failed, serving cached prices")
