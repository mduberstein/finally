"""Background task recording one portfolio-value snapshot on a fixed interval.

Placed in `app/portfolio`, not `app/market`, because a portfolio-value
snapshot is money, not price. `market/` stays about prices and must not
depend on the portfolio package — the same separation 03-RESEARCH.md's Open
Question 2 argues for the watchlist module.
"""

import asyncio
import logging
from collections.abc import Callable

from starlette.concurrency import run_in_threadpool

from app.market.cache import PriceCache

from .service import record_portfolio_snapshot

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 30.0


class SnapshotWriter:
    """Background task recording a portfolio snapshot every `interval`
    seconds, mirroring `MarketFeed`'s start/stop lifecycle and failure
    containment so the two background tasks behave identically.

    `record` is injected with a default rather than imported and called
    directly, so the lifecycle can be tested against a counting fake with
    no database at all — the same reason `MarketFeed` takes its source and
    ticker callable as constructor arguments.
    """

    def __init__(
        self,
        cache: PriceCache,
        interval: float = SNAPSHOT_INTERVAL_SECONDS,
        record: Callable[[PriceCache], float] = record_portfolio_snapshot,
    ) -> None:
        self._cache = cache
        self._interval = interval
        self._record = record
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the background recording loop.

        Raises `RuntimeError` if already running — starting twice would leak
        the first task, which would keep writing snapshots alongside the new
        one, the identical failure `MarketFeed.start()` guards against.
        """
        if self._task is not None and not self._task.done():
            raise RuntimeError("SnapshotWriter.start() called while already running")
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

    async def _run(self) -> None:
        # Sleep first, record after: the empty-state copy promises the first
        # snapshot "within 30 seconds", which a startup write would
        # contradict by making that empty state effectively unreachable.
        while True:
            await asyncio.sleep(self._interval)
            await self._tick()

    async def _tick(self) -> None:
        """Record once, containing any failure so one bad write never kills
        the only task recording portfolio history."""
        try:
            # The recorder opens a synchronous SQLite connection and must not
            # block the event loop also driving the price feed and every
            # open SSE stream.
            await run_in_threadpool(self._record, self._cache)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("portfolio snapshot write failed")
