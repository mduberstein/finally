"""Trade log repository behaviour."""

from app.db import trades


def test_no_trades_on_a_fresh_database(conn):
    assert trades.list_recent(conn) == []


def test_append_round_trips(conn):
    trade = trades.append(conn, "AAPL", "buy", 10.0, 195.0)
    assert trades.list_recent(conn) == [trade]
    assert trade.id
    assert trade.side == "buy"
    assert trade.executed_at


def test_list_recent_returns_newest_first(conn):
    for ticker in ("AAPL", "MSFT", "NVDA"):
        trades.append(conn, ticker, "buy", 1.0, 100.0)
    assert [t.ticker for t in trades.list_recent(conn)] == ["NVDA", "MSFT", "AAPL"]


def test_list_recent_honours_the_limit(conn):
    for ticker in ("AAPL", "MSFT", "NVDA"):
        trades.append(conn, ticker, "buy", 1.0, 100.0)
    assert [t.ticker for t in trades.list_recent(conn, limit=2)] == ["NVDA", "MSFT"]


def test_the_log_is_append_only_for_the_same_ticker(conn):
    trades.append(conn, "AAPL", "buy", 10.0, 195.0)
    trades.append(conn, "AAPL", "sell", 4.0, 198.0)
    assert len(trades.list_recent(conn)) == 2
