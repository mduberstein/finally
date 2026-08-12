"""A test client over a temporary database and a hand-loaded price cache.

`TestClient` is used without its context manager on purpose: entering it would
run the lifespan handler and start a real market feed. These tests drive the
cache themselves so prices are fixed and nothing polls in the background.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.market import PriceCache, Quote

PRICES = {"AAPL": 195.0, "MSFT": 400.0}


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Point DB_PATH at a fresh file so the real db/finally.db is never touched."""
    path = tmp_path / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path


@pytest.fixture
def cache(db_path):
    cache = PriceCache()
    for ticker, price in PRICES.items():
        set_price(cache, ticker, price)
    return cache


@pytest.fixture
def client(cache):
    return TestClient(create_app(cache))


def set_price(cache: PriceCache, ticker: str, price: float) -> None:
    """Move a ticker to a new price, the way a feed tick would."""
    cache.apply([Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))])
