import math

import pytest

from app.market import simulator as simulator_module
from app.market.simulator import DT, SimulatorSource


class TestSimulatorSourceDeterminism:
    async def test_same_seed_produces_identical_price_sequence(self):
        a = SimulatorSource(seed=42)
        b = SimulatorSource(seed=42)

        for _ in range(50):
            quotes_a = await a.fetch(["AAPL", "GOOGL"])
            quotes_b = await b.fetch(["AAPL", "GOOGL"])
            assert [q.price for q in quotes_a] == [q.price for q in quotes_b]

    async def test_different_seeds_diverge(self):
        a = SimulatorSource(seed=1)
        b = SimulatorSource(seed=2)

        for _ in range(20):
            prices_a = [q.price for q in await a.fetch(["AAPL"])]
            prices_b = [q.price for q in await b.fetch(["AAPL"])]
        assert prices_a != prices_b

    async def test_env_seed_is_used_when_no_explicit_seed(self, monkeypatch):
        monkeypatch.setenv("MARKET_SEED", "7")
        a = SimulatorSource()
        b = SimulatorSource(seed=7)

        for _ in range(10):
            quotes_a = await a.fetch(["AAPL"])
            quotes_b = await b.fetch(["AAPL"])
            assert [q.price for q in quotes_a] == [q.price for q in quotes_b]


class TestSimulatorSourcePositivity:
    async def test_prices_always_positive(self):
        source = SimulatorSource(seed=123)
        tickers = ["AAPL", "TSLA", "NVDA", "JPM"]

        for _ in range(2000):
            quotes = await source.fetch(tickers)
            assert all(q.price > 0 for q in quotes)


class TestSimulatorSourceFetch:
    async def test_returns_a_quote_per_requested_ticker(self):
        source = SimulatorSource(seed=1)
        quotes = await source.fetch(["AAPL", "GOOGL", "MSFT"])
        assert [q.ticker for q in quotes] == ["AAPL", "GOOGL", "MSFT"]

    async def test_empty_ticker_list_returns_empty(self):
        source = SimulatorSource(seed=1)
        assert await source.fetch([]) == []

    async def test_prices_a_ticker_it_has_never_seen(self):
        source = SimulatorSource(seed=1)
        quotes = await source.fetch(["ZZZZ"])
        assert quotes[0].price > 0

    async def test_lazy_initialization_starts_near_anchor(self):
        source = SimulatorSource(seed=1)
        quotes = await source.fetch(["AAPL"])
        # One tick of GBM at this dt moves price by a tiny fraction of a percent.
        assert quotes[0].price == pytest.approx(190.0, rel=0.01)

    async def test_poll_interval_is_tick_seconds(self):
        assert SimulatorSource.poll_interval == 0.5

    async def test_name_is_simulator(self):
        assert SimulatorSource(seed=1).name == "simulator"


class TestSimulatorSourceStatistics:
    """Statistical properties measured with events disabled — see design doc
    section 12: drama-event jumps are large and idiosyncratic enough to swamp
    the diffusion statistics otherwise."""

    async def test_realized_volatility_within_tolerance_of_configured_sigma(
        self, monkeypatch
    ):
        monkeypatch.setattr(simulator_module, "EVENT_PROBABILITY", 0.0)
        source = SimulatorSource(seed=99)
        ticker = "AAPL"
        configured_sigma = 0.28

        log_returns = []
        previous = None
        for _ in range(20000):
            price = (await source.fetch([ticker]))[0].price
            if previous is not None:
                log_returns.append(math.log(price / previous))
            previous = price

        n = len(log_returns)
        mean = sum(log_returns) / n
        variance = sum((r - mean) ** 2 for r in log_returns) / n
        realized_sigma = math.sqrt(variance / DT)

        assert realized_sigma == pytest.approx(configured_sigma, rel=0.35)

    async def test_correlation_ordering_tech_higher_than_cross_sector(
        self, monkeypatch
    ):
        monkeypatch.setattr(simulator_module, "EVENT_PROBABILITY", 0.0)
        source = SimulatorSource(seed=7)

        aapl, msft, jpm = [], [], []
        for _ in range(20000):
            quotes = await source.fetch(["AAPL", "MSFT", "JPM"])
            aapl.append(quotes[0].price)
            msft.append(quotes[1].price)
            jpm.append(quotes[2].price)

        def log_returns(prices):
            return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]

        def correlation(xs, ys):
            n = len(xs)
            mean_x, mean_y = sum(xs) / n, sum(ys) / n
            cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / n
            std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs) / n)
            std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys) / n)
            return cov / (std_x * std_y)

        r_aapl, r_msft, r_jpm = log_returns(aapl), log_returns(msft), log_returns(jpm)
        tech_corr = correlation(r_aapl, r_msft)
        cross_corr = correlation(r_aapl, r_jpm)

        assert tech_corr > cross_corr

    async def test_market_shock_is_shared_across_tickers_in_one_fetch(self, monkeypatch):
        """Drawing market_shock once per fetch (not per ticker) is what
        creates correlation — verified indirectly via a beta=1 ticker pair
        that must move identically before rounding/idiosyncratic noise."""
        monkeypatch.setattr(simulator_module, "EVENT_PROBABILITY", 0.0)
        source = SimulatorSource(seed=3)

        seen_shocks = []
        original_gauss = source._rng.gauss

        def spy_gauss(mu, sigma):
            value = original_gauss(mu, sigma)
            seen_shocks.append(value)
            return value

        source._rng.gauss = spy_gauss
        await source.fetch(["AAPL", "GOOGL", "MSFT"])
        # market_shock (1) + one idiosyncratic draw per ticker (3) = 4 draws.
        assert len(seen_shocks) == 4
