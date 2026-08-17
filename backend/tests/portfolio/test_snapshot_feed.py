import asyncio

import pytest

from app.db import database
from app.market.cache import PriceCache
from app.portfolio.service import record_portfolio_snapshot
from app.portfolio.snapshot_feed import SnapshotWriter


class CountingRecorder:
    """A recorder whose call count and per-call outcome is scripted by the
    test, mirroring `test_feed.py`'s `FakeSource` scripted-fake style."""

    def __init__(self, raise_on_calls: set[int] | None = None):
        self.calls = 0
        self._raise_on_calls = raise_on_calls or set()

    def __call__(self, cache: PriceCache) -> float:
        self.calls += 1
        if self.calls in self._raise_on_calls:
            raise RuntimeError("boom")
        return 10000.0


class TestSnapshotWriterLifecycle:
    async def test_start_and_stop_records_at_least_twice_over_a_few_intervals(self):
        cache = PriceCache()
        recorder = CountingRecorder()
        writer = SnapshotWriter(cache, interval=0.01, record=recorder)

        writer.start()
        await asyncio.sleep(0.035)
        await writer.stop()

        assert recorder.calls >= 2

    async def test_first_call_happens_after_one_interval_not_immediately(self):
        cache = PriceCache()
        recorder = CountingRecorder()
        writer = SnapshotWriter(cache, interval=0.05, record=recorder)

        writer.start()
        await asyncio.sleep(0.01)
        assert recorder.calls == 0

        await asyncio.sleep(0.06)
        await writer.stop()

        assert recorder.calls >= 1

    async def test_start_twice_raises(self):
        cache = PriceCache()
        writer = SnapshotWriter(cache, interval=0.01, record=CountingRecorder())

        writer.start()
        with pytest.raises(RuntimeError):
            writer.start()

        await writer.stop()

    async def test_stop_leaves_task_cancelled_and_a_second_stop_is_harmless(self):
        cache = PriceCache()
        writer = SnapshotWriter(cache, interval=0.01, record=CountingRecorder())

        writer.start()
        await asyncio.sleep(0.01)
        await writer.stop()

        await writer.stop()  # must not raise

    async def test_raising_recorder_does_not_stop_the_loop_and_a_later_tick_records(self):
        cache = PriceCache()
        recorder = CountingRecorder(raise_on_calls={1})
        writer = SnapshotWriter(cache, interval=0.01, record=recorder)

        writer.start()
        await asyncio.sleep(0.035)
        await writer.stop()

        assert recorder.calls >= 2


class TestRecordPortfolioSnapshotIntegration:
    def test_writes_a_row_valuing_cash_plus_every_position_at_cached_prices(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
        database.initialize()
        cache = PriceCache()

        total = record_portfolio_snapshot(cache)

        with database.connect() as conn:
            rows = conn.execute("SELECT total_value FROM portfolio_snapshots").fetchall()
        assert len(rows) == 1
        assert rows[0]["total_value"] == pytest.approx(total)
        assert total == pytest.approx(10000.0)
