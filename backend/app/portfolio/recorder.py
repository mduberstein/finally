"""Background task writing a portfolio value snapshot on a fixed interval."""

import asyncio
import logging

from starlette.concurrency import run_in_threadpool

from app.db import snapshots, transaction
from app.market import PriceCache

from .valuation import build_portfolio

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL = 30.0


def record_snapshot(cache: PriceCache) -> float:
    """Value the portfolio and append one snapshot row. Returns the total."""
    with transaction() as conn:
        portfolio = build_portfolio(conn, cache)
        snapshots.append(conn, portfolio.total_value)
    return portfolio.total_value


class SnapshotRecorder:
    """Records the portfolio total every `SNAPSHOT_INTERVAL` seconds.

    The database work runs in the threadpool because `sqlite3` blocks, and this
    task shares an event loop with every open SSE connection.

    Stopping signals an event rather than cancelling the task. Cancelling a task
    that is awaiting `run_in_threadpool` abandons the worker thread: the write
    finishes and commits after `stop()` has already returned, so shutdown would
    race the snapshot it was trying to end.
    """

    def __init__(self, cache: PriceCache, interval: float = SNAPSHOT_INTERVAL) -> None:
        self._cache = cache
        self._interval = interval
        self._stopping = asyncio.Event()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            raise RuntimeError("SnapshotRecorder.start() called while already running")
        self._stopping.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop after the current snapshot finishes, never mid-write."""
        task = self._task
        if task is None:
            return
        self._stopping.set()
        await task
        self._task = None

    async def _run(self) -> None:
        while True:
            if await self._stop_requested():
                return
            try:
                await run_in_threadpool(record_snapshot, self._cache)
            except Exception:
                logger.exception("portfolio snapshot failed")

    async def _stop_requested(self) -> bool:
        """Wait one interval. True if a stop arrived before it elapsed."""
        try:
            await asyncio.wait_for(self._stopping.wait(), self._interval)
        except TimeoutError:
            return False
        return True
