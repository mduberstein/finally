"""Trade execution: cash, share, and average-cost arithmetic."""

import pytest

from app.db import positions, profile, snapshots, trades, transaction
from app.portfolio import TradeError, execute_trade

from .conftest import set_price


def held(ticker: str):
    with transaction() as conn:
        return positions.get(conn, ticker)


def cash() -> float:
    with transaction() as conn:
        return profile.get_cash_balance(conn)


class TestBuy:
    def test_opens_a_position_and_debits_cash(self, cache):
        result = execute_trade(cache, "AAPL", "buy", 10)

        assert result.trade.ticker == "AAPL"
        assert result.trade.side == "buy"
        assert result.trade.price == 195.0
        assert result.cash_balance == 8050.0
        assert result.position.quantity == 10
        assert result.position.avg_cost == 195.0

    def test_ticker_is_upper_cased(self, cache):
        result = execute_trade(cache, "aapl", "buy", 1)

        assert result.trade.ticker == "AAPL"
        assert held("AAPL") is not None

    def test_second_buy_recomputes_weighted_average_cost(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)
        set_price(cache, "AAPL", 205.0)

        result = execute_trade(cache, "AAPL", "buy", 10)

        assert result.position.quantity == 20
        assert result.position.avg_cost == 200.0
        assert result.cash_balance == 10000.0 - 1950.0 - 2050.0

    def test_fractional_quantity(self, cache):
        result = execute_trade(cache, "AAPL", "buy", 0.5)

        assert result.position.quantity == 0.5
        assert result.cash_balance == 9902.5

    def test_insufficient_cash_names_both_amounts(self, cache):
        with pytest.raises(TradeError) as exc:
            execute_trade(cache, "MSFT", "buy", 100)

        assert exc.value.detail == "Insufficient cash: need $40000.00, have $10000.00"

    def test_insufficient_cash_leaves_nothing_behind(self, cache):
        with pytest.raises(TradeError):
            execute_trade(cache, "MSFT", "buy", 100)

        assert cash() == 10000.0
        assert held("MSFT") is None
        with transaction() as conn:
            assert trades.list_recent(conn) == []

    def test_spending_the_entire_balance_is_allowed(self, cache):
        result = execute_trade(cache, "AAPL", "buy", 10000 / 195.0)

        assert result.cash_balance == 0.0

    def test_unknown_ticker_has_no_price(self, cache):
        with pytest.raises(TradeError) as exc:
            execute_trade(cache, "ZZZZ", "buy", 1)

        assert exc.value.detail == "No price available for ZZZZ"


class TestSell:
    def test_partial_sell_keeps_average_cost(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)
        set_price(cache, "AAPL", 210.0)

        result = execute_trade(cache, "AAPL", "sell", 4)

        assert result.position.quantity == 6
        assert result.position.avg_cost == 195.0
        assert result.cash_balance == 10000.0 - 1950.0 + 840.0

    def test_selling_the_whole_position_closes_it(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)

        result = execute_trade(cache, "AAPL", "sell", 10)

        assert result.position is None
        assert held("AAPL") is None
        assert result.cash_balance == 10000.0

    def test_selling_at_a_loss_returns_less_cash(self, cache):
        execute_trade(cache, "AAPL", "buy", 10)
        set_price(cache, "AAPL", 150.0)

        result = execute_trade(cache, "AAPL", "sell", 10)

        assert result.cash_balance == 9550.0

    def test_fractional_sell(self, cache):
        execute_trade(cache, "AAPL", "buy", 1.5)

        result = execute_trade(cache, "AAPL", "sell", 0.25)

        assert result.position.quantity == 1.25

    def test_closing_a_position_built_from_inexact_fractions(self, cache):
        execute_trade(cache, "AAPL", "buy", 0.1)
        execute_trade(cache, "AAPL", "buy", 0.2)

        result = execute_trade(cache, "AAPL", "sell", 0.3)

        assert result.position is None

    def test_more_than_held_names_both_quantities(self, cache):
        execute_trade(cache, "AAPL", "buy", 3)

        with pytest.raises(TradeError) as exc:
            execute_trade(cache, "AAPL", "sell", 10)

        assert exc.value.detail == "Insufficient shares: tried to sell 10 AAPL, hold 3"

    def test_selling_a_ticker_never_held(self, cache):
        with pytest.raises(TradeError) as exc:
            execute_trade(cache, "TSLA", "sell", 2)

        assert exc.value.detail == "Insufficient shares: tried to sell 2 TSLA, hold 0"

    def test_failed_sell_leaves_the_position_untouched(self, cache):
        execute_trade(cache, "AAPL", "buy", 3)

        with pytest.raises(TradeError):
            execute_trade(cache, "AAPL", "sell", 10)

        assert held("AAPL").quantity == 3


class TestSideEffects:
    def test_every_trade_is_logged(self, cache):
        execute_trade(cache, "AAPL", "buy", 2)
        execute_trade(cache, "AAPL", "sell", 1)

        with transaction() as conn:
            log = trades.list_recent(conn)

        assert [(t.side, t.quantity) for t in log] == [("sell", 1), ("buy", 2)]

    def test_every_trade_records_a_snapshot(self, cache):
        execute_trade(cache, "AAPL", "buy", 2)
        execute_trade(cache, "AAPL", "buy", 2)

        with transaction() as conn:
            history = snapshots.list_recent(conn)

        assert len(history) == 2
        assert history[-1].total_value == 10000.0

    def test_snapshot_reflects_the_trade_that_caused_it(self, cache):
        set_price(cache, "AAPL", 195.0)
        execute_trade(cache, "AAPL", "buy", 10)
        set_price(cache, "AAPL", 200.0)

        execute_trade(cache, "AAPL", "buy", 10)

        with transaction() as conn:
            history = snapshots.list_recent(conn)

        assert history[-1].total_value == 10050.0
