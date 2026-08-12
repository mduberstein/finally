"""Positions repository behaviour."""

from app.db import positions


def test_no_positions_on_a_fresh_database(conn):
    assert positions.list_all(conn) == []
    assert positions.get(conn, "AAPL") is None


def test_upsert_inserts_and_round_trips(conn):
    created = positions.upsert(conn, "AAPL", 10.0, 190.0)
    stored = positions.get(conn, "AAPL")
    assert stored == created
    assert stored.quantity == 10.0
    assert stored.avg_cost == 190.0


def test_upsert_replaces_an_existing_position(conn):
    positions.upsert(conn, "AAPL", 10.0, 190.0)
    positions.upsert(conn, "AAPL", 15.0, 192.5)
    assert len(positions.list_all(conn)) == 1
    stored = positions.get(conn, "AAPL")
    assert stored.quantity == 15.0
    assert stored.avg_cost == 192.5


def test_fractional_quantities_survive(conn):
    positions.upsert(conn, "AAPL", 0.25, 190.0)
    assert positions.get(conn, "AAPL").quantity == 0.25


def test_list_all_is_alphabetical(conn):
    positions.upsert(conn, "MSFT", 1.0, 400.0)
    positions.upsert(conn, "AAPL", 1.0, 190.0)
    assert [p.ticker for p in positions.list_all(conn)] == ["AAPL", "MSFT"]


def test_delete_removes_and_reports_success(conn):
    positions.upsert(conn, "AAPL", 10.0, 190.0)
    assert positions.delete(conn, "AAPL")
    assert positions.get(conn, "AAPL") is None


def test_delete_reports_failure_when_nothing_is_held(conn):
    assert not positions.delete(conn, "AAPL")
