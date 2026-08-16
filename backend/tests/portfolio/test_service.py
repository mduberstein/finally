from datetime import UTC, datetime

import pytest

from app.db import database
from app.market.cache import PriceCache
from app.market.models import Quote
from app.portfolio.models import InsufficientCashError, UntradableTickerError
from app.portfolio.service import execute_trade, get_portfolio


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    database.initialize()


def _quote(ticker: str, price: float) -> Quote:
    return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))


class TestExecuteTradeBuy:
    def test_buy_decreases_cash_and_creates_position(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])

        result = execute_trade("AAPL", "buy", 10, cache)

        assert result.cash_balance == pytest.approx(10000.0 - 10 * 190.0)
        portfolio = get_portfolio(cache)
        assert portfolio["cash_balance"] == pytest.approx(10000.0 - 10 * 190.0)
        assert len(portfolio["positions"]) == 1
        assert portfolio["positions"][0]["avg_cost"] == pytest.approx(190.0)

        with database.connect() as conn:
            rows = conn.execute("SELECT side FROM trades").fetchall()
        assert len(rows) == 1
        assert rows[0]["side"] == "buy"

    def test_second_buy_produces_weighted_average_cost(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        execute_trade("AAPL", "buy", 10, cache)

        cache.apply([_quote("AAPL", 200.0)])
        execute_trade("AAPL", "buy", 10, cache)

        portfolio = get_portfolio(cache)
        assert len(portfolio["positions"]) == 1
        assert portfolio["positions"][0]["quantity"] == pytest.approx(20.0)
        assert portfolio["positions"][0]["avg_cost"] == pytest.approx(150.0)

        with database.connect() as conn:
            rows = conn.execute("SELECT side FROM trades").fetchall()
        assert len(rows) == 2

    def test_buy_costing_exactly_cash_balance_succeeds_and_zeroes_cash(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 1000.0)])

        result = execute_trade("AAPL", "buy", 10, cache)

        assert result.cash_balance == 0.0

    def test_buy_costing_one_cent_more_than_balance_is_rejected(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 1000.01)])

        with pytest.raises(InsufficientCashError):
            execute_trade("AAPL", "buy", 10, cache)

        portfolio = get_portfolio(cache)
        assert portfolio["cash_balance"] == 10000.0
        assert portfolio["positions"] == []
        with database.connect() as conn:
            rows = conn.execute("SELECT * FROM trades").fetchall()
        assert rows == []

    def test_buy_of_untradable_ticker_raises_and_writes_nothing(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        with pytest.raises(UntradableTickerError):
            execute_trade("ZZZZ", "buy", 10, cache)

        portfolio = get_portfolio(cache)
        assert portfolio["cash_balance"] == 10000.0
        assert portfolio["positions"] == []

    def test_lowercase_ticker_normalizes_and_succeeds(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])

        result = execute_trade("aapl", "buy", 5, cache)

        assert result.ticker == "AAPL"


class TestGetPortfolio:
    def test_fresh_database_has_no_positions(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        portfolio = get_portfolio(cache)

        assert portfolio["cash_balance"] == 10000.0
        assert portfolio["total_value"] == 10000.0
        assert portfolio["positions"] == []
