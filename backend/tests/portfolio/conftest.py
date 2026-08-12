"""A temporary database and a hand-loaded price cache — no feed, no network."""

from datetime import UTC, datetime

import pytest

from app.market import PriceCache, Quote

PRICES = {"AAPL": 195.0, "MSFT": 400.0, "TSLA": 250.0}


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Point DB_PATH at a fresh file so the real db/finally.db is never touched."""
    path = tmp_path / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path


@pytest.fixture
def cache(db_path):
    """A cache pre-populated with fixed prices, so trades fill at known values."""
    return make_cache(PRICES)


def make_cache(prices: dict[str, float]) -> PriceCache:
    cache = PriceCache()
    for ticker, price in prices.items():
        set_price(cache, ticker, price)
    return cache


def set_price(cache: PriceCache, ticker: str, price: float) -> None:
    """Move a ticker to a new price, the way a feed tick would."""
    cache.apply([Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))])
