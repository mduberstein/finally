"""Valuing held positions against the cache: P&L, percentages, weights."""

from app.db import positions, profile, transaction
from app.portfolio import load_portfolio

from .conftest import make_cache


def given(cash: float, held: dict[str, tuple[float, float]]) -> None:
    """Set the cash balance and the open positions directly, without trading."""
    with transaction() as conn:
        profile.set_cash_balance(conn, cash)
        for ticker, (quantity, avg_cost) in held.items():
            positions.upsert(conn, ticker, quantity, avg_cost)


class TestEmptyPortfolio:
    def test_is_all_cash(self, cache):
        portfolio = load_portfolio(cache)

        assert portfolio.cash_balance == 10000.0
        assert portfolio.positions_value == 0.0
        assert portfolio.total_value == 10000.0
        assert portfolio.positions == []

    def test_reports_zero_pnl_rather_than_dividing_by_zero(self, cache):
        portfolio = load_portfolio(cache)

        assert portfolio.total_unrealized_pnl == 0.0
        assert portfolio.total_unrealized_pnl_percent == 0.0


class TestValuedPositions:
    def test_matches_the_contract_example(self, cache):
        given(8050.0, {"AAPL": (10.0, 190.0)})

        portfolio = load_portfolio(cache)
        position = portfolio.positions[0]

        assert portfolio.positions_value == 1950.0
        assert portfolio.total_value == 10000.0
        assert portfolio.total_unrealized_pnl == 50.0
        assert portfolio.total_unrealized_pnl_percent == 2.63
        assert position.current_price == 195.0
        assert position.market_value == 1950.0
        assert position.unrealized_pnl == 50.0
        assert position.unrealized_pnl_percent == 2.63
        assert position.weight == 0.195

    def test_a_losing_position_reports_negative_pnl(self, cache):
        given(9000.0, {"AAPL": (10.0, 250.0)})

        portfolio = load_portfolio(cache)

        assert portfolio.total_unrealized_pnl == -550.0
        assert portfolio.positions[0].unrealized_pnl_percent == -22.0

    def test_weights_are_fractions_of_total_value(self, cache):
        given(0.0, {"AAPL": (10.0, 195.0), "MSFT": (10.0, 400.0)})

        portfolio = load_portfolio(cache)
        weights = {p.ticker: p.weight for p in portfolio.positions}

        assert weights == {"AAPL": 0.3277, "MSFT": 0.6723}
        assert portfolio.total_value == 5950.0

    def test_an_unpriced_ticker_falls_back_to_its_cost(self, cache):
        given(5000.0, {"ZZZZ": (10.0, 40.0)})

        portfolio = load_portfolio(cache)
        position = portfolio.positions[0]

        assert position.current_price == 40.0
        assert position.market_value == 400.0
        assert position.unrealized_pnl == 0.0

    def test_fractional_quantities_are_valued(self, cache):
        given(0.0, {"AAPL": (0.5, 100.0)})

        portfolio = load_portfolio(cache)

        assert portfolio.positions[0].market_value == 97.5
        assert portfolio.positions[0].unrealized_pnl == 47.5

    def test_positions_are_listed_alphabetically(self, cache):
        given(0.0, {"TSLA": (1.0, 250.0), "AAPL": (1.0, 195.0), "MSFT": (1.0, 400.0)})

        portfolio = load_portfolio(cache)

        assert [p.ticker for p in portfolio.positions] == ["AAPL", "MSFT", "TSLA"]


class TestPriceChanges:
    def test_revaluing_after_a_price_move(self, cache):
        given(0.0, {"AAPL": (10.0, 195.0)})
        assert load_portfolio(cache).total_value == 1950.0

        moved = make_cache({"AAPL": 200.0})

        assert load_portfolio(moved).total_value == 2000.0
