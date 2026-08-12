"""The periodic portfolio value snapshot task."""

import asyncio
import time

import pytest

from app.db import positions, snapshots, transaction
from app.portfolio import SNAPSHOT_INTERVAL, SnapshotRecorder, record_snapshot


def recorded() -> list[float]:
    with transaction() as conn:
        return [snapshot.total_value for snapshot in snapshots.list_recent(conn)]


class TestRecordSnapshot:
    def test_records_the_current_total(self, cache):
        with transaction() as conn:
            positions.upsert(conn, "AAPL", 10.0, 190.0)

        assert record_snapshot(cache) == 11950.0
        assert recorded() == [11950.0]


class TestSnapshotRecorder:
    def test_interval_is_thirty_seconds(self):
        assert SNAPSHOT_INTERVAL == 30.0

    async def test_records_on_each_tick_until_stopped(self, cache):
        recorder = SnapshotRecorder(cache, interval=0.01)
        recorder.start()
        await asyncio.sleep(0.05)
        await recorder.stop()

        written = len(recorded())
        assert written >= 2

        await asyncio.sleep(0.05)
        assert len(recorded()) == written

    async def test_stop_waits_for_a_snapshot_already_in_flight(self, cache, monkeypatch):
        """Cancelling the task instead of signalling it would abandon this write.

        `run_in_threadpool` cannot cancel a running thread, so a cancelled task
        returns from `stop()` while the write is still on its way to the disk.
        """
        finished = []

        def slow(_cache):
            time.sleep(0.05)
            finished.append(1)

        monkeypatch.setattr("app.portfolio.recorder.record_snapshot", slow)
        recorder = SnapshotRecorder(cache, interval=0.001)
        recorder.start()
        await asyncio.sleep(0.02)
        await recorder.stop()

        assert finished == [1]

    async def test_starting_twice_would_leak_the_first_task(self, cache):
        recorder = SnapshotRecorder(cache, interval=0.01)
        recorder.start()
        try:
            with pytest.raises(RuntimeError):
                recorder.start()
        finally:
            await recorder.stop()

    async def test_stopping_an_unstarted_recorder_is_harmless(self, cache):
        await SnapshotRecorder(cache).stop()

    async def test_a_failed_snapshot_does_not_kill_the_loop(self, cache, monkeypatch):
        failures = []

        def boom(_cache):
            failures.append(1)
            raise RuntimeError("database is locked")

        monkeypatch.setattr("app.portfolio.recorder.record_snapshot", boom)
        recorder = SnapshotRecorder(cache, interval=0.01)
        recorder.start()
        await asyncio.sleep(0.05)
        await recorder.stop()

        assert len(failures) >= 2
