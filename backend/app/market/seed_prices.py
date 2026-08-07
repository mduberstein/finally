import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TickerProfile:
    """Static characteristics of a simulated ticker."""

    anchor: float
    """Price the random walk is pulled back toward."""

    volatility: float
    """Annualised volatility, e.g. 0.28 for 28%."""

    beta: float
    """Correlation with the shared market factor, 0 to 1."""


PROFILES: dict[str, TickerProfile] = {
    "AAPL": TickerProfile(190.0, 0.28, 0.85),
    "GOOGL": TickerProfile(175.0, 0.32, 0.85),
    "MSFT": TickerProfile(420.0, 0.26, 0.85),
    "AMZN": TickerProfile(185.0, 0.35, 0.80),
    "TSLA": TickerProfile(250.0, 0.60, 0.70),
    "NVDA": TickerProfile(880.0, 0.55, 0.75),
    "META": TickerProfile(500.0, 0.38, 0.80),
    "JPM": TickerProfile(200.0, 0.22, 0.50),
    "V": TickerProfile(280.0, 0.20, 0.55),
    "NFLX": TickerProfile(610.0, 0.40, 0.65),
}

DEFAULT_VOLATILITY = 0.35
DEFAULT_BETA = 0.70


def profile_for(ticker: str) -> TickerProfile:
    """Profile for a known ticker, or a deterministic synthetic one."""
    if ticker in PROFILES:
        return PROFILES[ticker]

    digest = hashlib.md5(ticker.encode()).hexdigest()
    anchor = 20.0 + (int(digest[:8], 16) % 38000) / 100.0
    return TickerProfile(anchor, DEFAULT_VOLATILITY, DEFAULT_BETA)
