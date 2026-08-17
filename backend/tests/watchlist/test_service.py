import pytest

from app.db import database
from app.watchlist.models import DuplicateTickerError, InvalidTickerError, WatchlistFullError
from app.watchlist.service import MAX_WATCHLIST_TICKERS, add_ticker, remove_ticker


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    database.initialize()
    # Start from an empty watchlist so cap and duplicate tests are deterministic.
    with database.connect() as conn:
        conn.execute("DELETE FROM watchlist")


class TestAddTicker:
    def test_add_normalizes_and_inserts_exactly_one_row(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)

        result = add_ticker(" aapl ")

        assert result == "AAPL"
        assert database.watchlist_tickers() == ["AAPL"]

    def test_add_duplicate_raises_and_leaves_row_count_unchanged(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        add_ticker("AAPL")

        with pytest.raises(DuplicateTickerError):
            add_ticker("AAPL")

        assert database.watchlist_tickers() == ["AAPL"]

    @pytest.mark.parametrize("bad_ticker", ["AA1", "AA-PL", "", "ABCDEFGHIJK"])
    def test_add_malformed_symbol_raises_and_writes_nothing(
        self, tmp_path, monkeypatch, bad_ticker
    ):
        _use_tmp_db(tmp_path, monkeypatch)

        with pytest.raises(InvalidTickerError):
            add_ticker(bad_ticker)

        assert database.watchlist_tickers() == []

    def test_add_past_cap_raises_and_writes_nothing(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        # Letters-only synthetic tickers -- normalize_ticker rejects digits.
        synthetic_tickers = [
            chr(65 + i // 26) + chr(65 + i % 26) for i in range(MAX_WATCHLIST_TICKERS)
        ]
        for ticker in synthetic_tickers:
            add_ticker(ticker)

        with pytest.raises(WatchlistFullError):
            add_ticker("OVER")

        assert len(database.watchlist_tickers()) == MAX_WATCHLIST_TICKERS
        assert "OVER" not in database.watchlist_tickers()


class TestRemoveTicker:
    def test_remove_seeded_ticker_returns_true_and_removes_row(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        add_ticker("AAPL")

        removed = remove_ticker(" aapl ")

        assert removed is True
        assert "AAPL" not in database.watchlist_tickers()

    def test_remove_absent_ticker_returns_false_and_leaves_others_untouched(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        add_ticker("AAPL")

        removed = remove_ticker("GOOGL")

        assert removed is False
        assert database.watchlist_tickers() == ["AAPL"]

    def test_remove_malformed_symbol_raises_before_touching_database(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        add_ticker("AAPL")

        with pytest.raises(InvalidTickerError):
            remove_ticker("AA1")

        assert database.watchlist_tickers() == ["AAPL"]
