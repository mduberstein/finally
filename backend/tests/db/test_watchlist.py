"""Watchlist repository behaviour."""

import sqlite3

import pytest

from app.db import watchlist
from app.db.seed import DEFAULT_TICKERS


def test_list_all_returns_the_seeded_tickers_in_order(conn):
    assert [entry.ticker for entry in watchlist.list_all(conn)] == list(DEFAULT_TICKERS)


def test_add_round_trips(conn):
    entry = watchlist.add(conn, "PYPL")
    assert entry.ticker == "PYPL"
    assert entry.added_at
    assert "PYPL" in [e.ticker for e in watchlist.list_all(conn)]


def test_add_rejects_a_duplicate_ticker(conn):
    with pytest.raises(sqlite3.IntegrityError):
        watchlist.add(conn, "AAPL")


def test_exists_reflects_membership(conn):
    assert watchlist.exists(conn, "AAPL")
    assert not watchlist.exists(conn, "PYPL")


def test_remove_deletes_and_reports_success(conn):
    assert watchlist.remove(conn, "AAPL")
    assert not watchlist.exists(conn, "AAPL")


def test_remove_reports_failure_for_an_unwatched_ticker(conn):
    assert not watchlist.remove(conn, "PYPL")
