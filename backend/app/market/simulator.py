"""Geometric Brownian motion market data simulator."""

import math
import os
import random
from collections.abc import Sequence
from datetime import UTC, datetime

from .interface import MarketDataSource
from .models import Quote
from .seed_prices import profile_for

TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
TICK_SECONDS = 0.5
DT = TICK_SECONDS / TRADING_SECONDS_PER_YEAR

KAPPA = 175.0
"""Anchor pull strength. ln(2) * 252 gives a one-session half-life."""

EVENT_PROBABILITY = 8e-5
EVENT_MIN, EVENT_MAX = 0.02, 0.05


class SimulatorSource(MarketDataSource):
    """Geometric Brownian motion price simulator.

    Prices are pulled back toward a per-ticker anchor (an Ornstein-Uhlenbeck
    process in log space) instead of drifting unboundedly, correlated across
    tickers via one shared market factor per tick, and occasionally jump 2-5%
    for demo drama. Positivity is guaranteed by the GBM structure itself, not
    by clamping.
    """

    name = "simulator"
    poll_interval = TICK_SECONDS

    def __init__(self, seed: int | None = None) -> None:
        if seed is None:
            env_seed = os.getenv("MARKET_SEED")
            seed = int(env_seed) if env_seed else None
        self._rng = random.Random(seed)
        self._prices: dict[str, float] = {}

    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        """Advance every requested ticker one tick."""
        market_shock = self._rng.gauss(0, 1)
        now = datetime.now(UTC)
        return [
            Quote(ticker, self._advance(ticker, market_shock), now) for ticker in tickers
        ]

    def _advance(self, ticker: str, market_shock: float) -> float:
        profile = profile_for(ticker)
        price = self._prices.get(ticker, profile.anchor)
        sigma = profile.volatility

        shock = profile.beta * market_shock + math.sqrt(1 - profile.beta**2) * self._rng.gauss(
            0, 1
        )

        pull = KAPPA * math.log(profile.anchor / price) * DT
        ito = -0.5 * sigma**2 * DT
        diffusion = sigma * math.sqrt(DT) * shock

        price *= math.exp(pull + ito + diffusion)
        price *= self._event_multiplier()

        self._prices[ticker] = price
        return round(price, 2)

    def _event_multiplier(self) -> float:
        """Occasional 2-5% jump for drama. Returns 1.0 most ticks."""
        if self._rng.random() >= EVENT_PROBABILITY:
            return 1.0
        magnitude = self._rng.uniform(EVENT_MIN, EVENT_MAX)
        return 1 + magnitude if self._rng.random() < 0.5 else 1 - magnitude
