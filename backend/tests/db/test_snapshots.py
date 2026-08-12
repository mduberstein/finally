"""Portfolio snapshot repository behaviour."""

from app.db import snapshots


def test_no_snapshots_on_a_fresh_database(conn):
    assert snapshots.list_recent(conn) == []


def test_append_round_trips(conn):
    snapshot = snapshots.append(conn, 10000.0)
    assert snapshots.list_recent(conn) == [snapshot]
    assert snapshot.total_value == 10000.0
    assert snapshot.recorded_at


def test_list_recent_is_ascending_in_time(conn):
    for value in (10000.0, 10100.0, 10200.0):
        snapshots.append(conn, value)
    assert [s.total_value for s in snapshots.list_recent(conn)] == [10000.0, 10100.0, 10200.0]


def test_the_limit_keeps_the_newest_and_still_returns_them_ascending(conn):
    for value in (10000.0, 10100.0, 10200.0):
        snapshots.append(conn, value)
    assert [s.total_value for s in snapshots.list_recent(conn, limit=2)] == [10100.0, 10200.0]
