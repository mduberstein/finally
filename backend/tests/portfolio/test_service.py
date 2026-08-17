import threading
from datetime import UTC, datetime

import pytest

from app.db import database
from app.market.cache import PriceCache
from app.market.models import Quote
from app.portfolio.models import (
    InsufficientCashError,
    InsufficientSharesError,
    UntradableTickerError,
)
from app.portfolio.service import (
    execute_trade,
    get_portfolio,
    get_portfolio_history,
    record_portfolio_snapshot,
)


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


class TestExecuteTradeSell:
    def test_partial_sell_increases_cash_and_reduces_position(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        execute_trade("AAPL", "buy", 10, cache)

        result = execute_trade("AAPL", "sell", 4, cache)

        expected_cash = 10000.0 - 10 * 190.0 + 4 * 190.0
        assert result.cash_balance == pytest.approx(expected_cash)
        portfolio = get_portfolio(cache)
        assert portfolio["cash_balance"] == pytest.approx(expected_cash)
        assert len(portfolio["positions"]) == 1
        assert portfolio["positions"][0]["quantity"] == pytest.approx(6.0)
        assert portfolio["positions"][0]["avg_cost"] == pytest.approx(190.0)

    def test_selling_all_shares_removes_position_row(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        execute_trade("AAPL", "buy", 10, cache)

        result = execute_trade("AAPL", "sell", 10, cache)

        assert result.cash_balance == pytest.approx(10000.0)
        portfolio = get_portfolio(cache)
        assert portfolio["positions"] == []

    def test_oversell_by_one_share_raises_insufficient_shares(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        execute_trade("AAPL", "buy", 10, cache)

        with pytest.raises(InsufficientSharesError) as excinfo:
            execute_trade("AAPL", "sell", 11, cache)
        assert excinfo.value.detail()["owned"] == 10

        portfolio = get_portfolio(cache)
        assert portfolio["cash_balance"] == pytest.approx(10000.0 - 10 * 190.0)
        assert portfolio["positions"][0]["quantity"] == pytest.approx(10.0)
        with database.connect() as conn:
            rows = conn.execute("SELECT * FROM trades").fetchall()
        assert len(rows) == 1

    def test_selling_ticker_with_no_position_raises_insufficient_shares_owned_zero(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])

        with pytest.raises(InsufficientSharesError) as excinfo:
            execute_trade("AAPL", "sell", 1, cache)
        assert excinfo.value.detail()["owned"] == 0

    def test_rejected_sell_leaves_state_unchanged(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        execute_trade("AAPL", "buy", 5, cache)
        before = get_portfolio(cache)

        with pytest.raises(InsufficientSharesError):
            execute_trade("AAPL", "sell", 6, cache)

        after = get_portfolio(cache)
        assert after == before
        with database.connect() as conn:
            rows = conn.execute("SELECT * FROM trades").fetchall()
        assert len(rows) == 1

    def test_every_accepted_sell_appends_one_trade_row(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        execute_trade("AAPL", "buy", 10, cache)
        execute_trade("AAPL", "sell", 4, cache)
        execute_trade("AAPL", "sell", 6, cache)

        with database.connect() as conn:
            rows = conn.execute("SELECT side FROM trades ORDER BY executed_at").fetchall()
        assert [row["side"] for row in rows] == ["buy", "sell", "sell"]


class TestGetPortfolio:
    def test_fresh_database_has_no_positions(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        portfolio = get_portfolio(cache)

        assert portfolio["cash_balance"] == 10000.0
        assert portfolio["total_value"] == 10000.0
        assert portfolio["positions"] == []

    def test_total_value_equals_cash_plus_positions_and_pnl_math(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0), _quote("GOOGL", 50.0)])
        execute_trade("AAPL", "buy", 10, cache)
        execute_trade("GOOGL", "buy", 20, cache)

        cache.apply([_quote("AAPL", 120.0), _quote("GOOGL", 40.0)])
        portfolio = get_portfolio(cache)

        expected_positions_value = 10 * 120.0 + 20 * 40.0
        assert portfolio["total_value"] == pytest.approx(
            portfolio["cash_balance"] + expected_positions_value
        )
        by_ticker = {p["ticker"]: p for p in portfolio["positions"]}
        assert by_ticker["AAPL"]["unrealized_pnl"] == pytest.approx(10 * (120.0 - 100.0))
        assert by_ticker["GOOGL"]["unrealized_pnl"] == pytest.approx(20 * (40.0 - 50.0))


class TestAppendOnlyTradeHistory:
    def test_trade_history_count_only_increases_and_rejected_trade_adds_no_row(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])

        execute_trade("AAPL", "buy", 10, cache)
        with database.connect() as conn:
            first_rows = [dict(row) for row in conn.execute("SELECT * FROM trades").fetchall()]
        assert len(first_rows) == 1

        with pytest.raises(InsufficientSharesError):
            execute_trade("AAPL", "sell", 999, cache)
        with database.connect() as conn:
            after_reject_rows = [
                dict(row) for row in conn.execute("SELECT * FROM trades").fetchall()
            ]
        assert after_reject_rows == first_rows

        execute_trade("AAPL", "sell", 5, cache)
        with database.connect() as conn:
            final_rows = conn.execute("SELECT * FROM trades").fetchall()
        assert len(final_rows) == 2


class TestConcurrentTrades:
    def test_only_one_of_two_racing_buys_succeeds_when_only_one_is_affordable(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        # Cash balance is 10000.0; each buy costs 6000.0, so exactly one fits.
        cache.apply([_quote("AAPL", 600.0)])

        results: list[object] = []
        barrier = threading.Barrier(2)

        def run_trade() -> None:
            barrier.wait()
            try:
                results.append(execute_trade("AAPL", "buy", 10, cache))
            except InsufficientCashError as error:
                results.append(error)

        threads = [threading.Thread(target=run_trade) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, InsufficientCashError)]
        assert len(successes) == 1
        assert len(failures) == 1

        portfolio = get_portfolio(cache)
        assert portfolio["cash_balance"] == pytest.approx(10000.0 - 6000.0)


class TestTradeSnapshots:
    def test_buy_writes_exactly_one_snapshot_row_matching_executed_at(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])

        result = execute_trade("AAPL", "buy", 10, cache)

        with database.connect() as conn:
            rows = conn.execute("SELECT recorded_at FROM portfolio_snapshots").fetchall()
        assert len(rows) == 1
        assert rows[0]["recorded_at"] == result.executed_at

    def test_snapshot_total_value_prices_every_position_not_just_the_traded_one(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0), _quote("GOOGL", 50.0)])
        execute_trade("AAPL", "buy", 10, cache)

        cache.apply([_quote("GOOGL", 60.0)])
        result = execute_trade("GOOGL", "buy", 5, cache)

        with database.connect() as conn:
            rows = conn.execute(
                "SELECT total_value FROM portfolio_snapshots ORDER BY rowid"
            ).fetchall()
        assert len(rows) == 2
        expected_total = result.cash_balance + 10 * 100.0 + 5 * 60.0
        assert rows[-1]["total_value"] == pytest.approx(expected_total)

    def test_rejected_trade_writes_no_snapshot_row(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 1000.01)])

        with pytest.raises(InsufficientCashError):
            execute_trade("AAPL", "buy", 10, cache)

        with database.connect() as conn:
            rows = conn.execute("SELECT * FROM portfolio_snapshots").fetchall()
        assert rows == []


class TestGetPortfolioHistory:
    def test_fresh_database_returns_empty_list(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)

        assert get_portfolio_history() == []

    def test_returns_rows_ascending_by_recorded_at_after_interleaved_trades(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        execute_trade("AAPL", "buy", 1, cache)

        cache.apply([_quote("AAPL", 110.0)])
        execute_trade("AAPL", "buy", 1, cache)

        cache.apply([_quote("AAPL", 120.0)])
        execute_trade("AAPL", "sell", 1, cache)

        history = get_portfolio_history()

        assert len(history) == 3
        recorded_ats = [point["recorded_at"] for point in history]
        assert recorded_ats == sorted(recorded_ats)

    def test_two_snapshots_with_identical_recorded_at_both_survive_in_stable_order(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        same_timestamp = "2026-01-01T00:00:00+00:00"
        with database.connect() as conn, conn:
            conn.execute(
                "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
                "VALUES (?, 'default', ?, ?)",
                ("snap-a", 10000.0, same_timestamp),
            )
            conn.execute(
                "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
                "VALUES (?, 'default', ?, ?)",
                ("snap-b", 10500.0, same_timestamp),
            )

        history = get_portfolio_history()

        assert len(history) == 2
        assert [point["total_value"] for point in history] == [10000.0, 10500.0]


class TestRecordPortfolioSnapshot:
    def test_records_a_row_valuing_cash_plus_every_position_at_cached_prices(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0), _quote("GOOGL", 50.0)])
        execute_trade("AAPL", "buy", 10, cache)
        execute_trade("GOOGL", "buy", 4, cache)

        cache.apply([_quote("AAPL", 120.0), _quote("GOOGL", 55.0)])
        total = record_portfolio_snapshot(cache)

        portfolio = get_portfolio(cache)
        assert total == pytest.approx(portfolio["total_value"])
        with database.connect() as conn:
            rows = conn.execute("SELECT total_value FROM portfolio_snapshots").fetchall()
        assert any(row["total_value"] == pytest.approx(total) for row in rows)
