import asyncio
import math

import pytest

from app.market import seed_prices, simulator
from app.market.seed_prices import PROFILES, profile_for
from app.market.simulator import SimulatorSource


async def run_ticks(source: SimulatorSource, tickers: list[str], n: int) -> dict[str, list[float]]:
    history: dict[str, list[float]] = {ticker: [] for ticker in tickers}
    for _ in range(n):
        quotes = await source.fetch(tickers)
        for q in quotes:
            history[q.ticker].append(q.price)
    return history


def test_determinism_same_seed_same_prices():
    async def _run():
        source_a = SimulatorSource(seed=42)
        source_b = SimulatorSource(seed=42)
        history_a = await run_ticks(source_a, ["AAPL", "TSLA"], 200)
        history_b = await run_ticks(source_b, ["AAPL", "TSLA"], 200)
        return history_a, history_b

    history_a, history_b = asyncio.run(_run())
    assert history_a == history_b


def test_different_seeds_diverge():
    async def _run():
        source_a = SimulatorSource(seed=1)
        source_b = SimulatorSource(seed=2)
        history_a = await run_ticks(source_a, ["AAPL"], 50)
        history_b = await run_ticks(source_b, ["AAPL"], 50)
        return history_a, history_b

    history_a, history_b = asyncio.run(_run())
    assert history_a != history_b


def test_prices_are_always_positive(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROBABILITY", 8e-5)

    async def _run():
        source = SimulatorSource(seed=7)
        history = await run_ticks(source, ["AAPL", "TSLA", "NVDA"], 20_000)
        return history

    history = asyncio.run(_run())
    for prices in history.values():
        assert all(price > 0 for price in prices)


def test_env_seed_used_when_no_explicit_seed(monkeypatch):
    monkeypatch.setenv("MARKET_SEED", "123")
    source_a = SimulatorSource()
    source_b = SimulatorSource(seed=123)

    async def _run():
        return await run_ticks(source_a, ["AAPL"], 20), await run_ticks(source_b, ["AAPL"], 20)

    history_a, history_b = asyncio.run(_run())
    assert history_a == history_b


def test_realised_volatility_close_to_configured_sigma(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROBABILITY", 0.0)

    async def _run():
        source = SimulatorSource(seed=99)
        return await run_ticks(source, ["AAPL"], 20_000)

    history = asyncio.run(_run())["AAPL"]

    log_returns = [math.log(b / a) for a, b in zip(history, history[1:])]
    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)
    realised_sigma = math.sqrt(variance / simulator.DT)

    configured_sigma = PROFILES["AAPL"].volatility
    relative_error = abs(realised_sigma - configured_sigma) / configured_sigma
    assert relative_error < 0.25


def test_correlation_ordering_tech_vs_cross_sector(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROBABILITY", 0.0)

    async def _run():
        source = SimulatorSource(seed=99)
        return await run_ticks(source, ["AAPL", "MSFT", "JPM"], 20_000)

    history = asyncio.run(_run())

    def log_returns(prices: list[float]) -> list[float]:
        return [math.log(b / a) for a, b in zip(prices, prices[1:])]

    def correlation(xs: list[float], ys: list[float]) -> float:
        mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        var_x = sum((x - mean_x) ** 2 for x in xs)
        var_y = sum((y - mean_y) ** 2 for y in ys)
        return cov / math.sqrt(var_x * var_y)

    aapl, msft, jpm = (log_returns(history[t]) for t in ("AAPL", "MSFT", "JPM"))
    corr_tech = correlation(aapl, msft)
    corr_cross_sector = correlation(aapl, jpm)

    assert corr_tech > corr_cross_sector


def test_event_probability_produces_occasional_jumps(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROBABILITY", 0.5)

    async def _run():
        source = SimulatorSource(seed=3)
        return await run_ticks(source, ["AAPL"], 200)

    history = asyncio.run(_run())["AAPL"]
    changes = [abs(b / a - 1) for a, b in zip(history, history[1:])]
    assert any(change > 0.01 for change in changes)


def test_profile_for_known_ticker_returns_exact_profile():
    assert profile_for("AAPL") == PROFILES["AAPL"]


def test_profile_for_unknown_ticker_is_deterministic():
    first = profile_for("PYPL")
    second = profile_for("PYPL")
    assert first == second


def test_profile_for_unknown_ticker_within_expected_range():
    for ticker in ["PYPL", "AMD", "BRK.B", "SOME-NEW-TICKER"]:
        profile = profile_for(ticker)
        assert 20.0 <= profile.anchor <= 399.99
        assert profile.volatility == seed_prices.DEFAULT_VOLATILITY
        assert profile.beta == seed_prices.DEFAULT_BETA


def test_profile_for_unknown_tickers_differ():
    anchors = {profile_for(t).anchor for t in ["PYPL", "AMD", "BRK.B"]}
    assert len(anchors) > 1


def test_fetch_omits_nothing_for_requested_tickers():
    async def _run():
        source = SimulatorSource(seed=1)
        return await source.fetch(["AAPL", "MADE-UP-TICKER"])

    quotes = asyncio.run(_run())
    assert {q.ticker for q in quotes} == {"AAPL", "MADE-UP-TICKER"}


def test_fetch_empty_tickers_returns_empty_list():
    async def _run():
        source = SimulatorSource(seed=1)
        return await source.fetch([])

    assert asyncio.run(_run()) == []


@pytest.mark.asyncio
async def test_aclose_is_a_noop():
    source = SimulatorSource(seed=1)
    await source.aclose()
