"""The one environment-aware seam that selects a market data source."""

import os

from .interface import MarketDataSource
from .massive import MassiveSource
from .simulator import SimulatorSource


def create_source() -> MarketDataSource:
    """The one place that decides which market data source is live."""
    api_key = os.getenv("MASSIVE_API_KEY", "").strip()
    if api_key:
        interval_raw = os.getenv("MARKET_POLL_INTERVAL", "15")
        try:
            interval = float(interval_raw)
        except ValueError:
            interval = 15.0
        return MassiveSource(api_key, poll_interval=interval)
    return SimulatorSource()
