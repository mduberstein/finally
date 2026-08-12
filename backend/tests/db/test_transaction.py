"""The unit-of-work primitive that keeps a trade atomic."""

import pytest

from app.db import positions, profile, trades, transaction


def test_changes_commit_on_success(db_path):
    with transaction() as conn:
        profile.set_cash_balance(conn, 8050.0)

    with transaction() as conn:
        assert profile.get_cash_balance(conn) == 8050.0


def test_exception_rolls_back_every_write(db_path):
    with pytest.raises(RuntimeError, match="price feed died"):
        with transaction() as conn:
            profile.set_cash_balance(conn, 8050.0)
            positions.upsert(conn, "AAPL", 10.0, 195.0)
            trades.append(conn, "AAPL", "buy", 10.0, 195.0)
            raise RuntimeError("price feed died")

    with transaction() as conn:
        assert profile.get_cash_balance(conn) == 10000.0
        assert positions.get(conn, "AAPL") is None
        assert trades.list_recent(conn) == []


def test_a_trade_commits_all_three_writes_together(db_path):
    with transaction() as conn:
        profile.set_cash_balance(conn, 8050.0)
        positions.upsert(conn, "AAPL", 10.0, 195.0)
        trades.append(conn, "AAPL", "buy", 10.0, 195.0)

    with transaction() as conn:
        assert profile.get_cash_balance(conn) == 8050.0
        assert positions.get(conn, "AAPL").quantity == 10.0
        assert len(trades.list_recent(conn)) == 1


def test_database_is_usable_after_a_rollback(db_path):
    with pytest.raises(ZeroDivisionError):
        with transaction() as conn:
            positions.upsert(conn, "AAPL", 10.0, 195.0)
            1 / 0

    with transaction() as conn:
        positions.upsert(conn, "MSFT", 5.0, 400.0)

    with transaction() as conn:
        assert [p.ticker for p in positions.list_all(conn)] == ["MSFT"]
