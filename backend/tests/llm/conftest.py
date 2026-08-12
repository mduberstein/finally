"""Fixtures for the assistant tests. The real API is never called."""

from datetime import UTC, datetime

import pytest

from app.db import transaction
from app.db.models import Trade, new_id
from app.market.cache import PriceCache
from app.market.models import Quote
from app.portfolio import TradeError, TradeResult

SEEDED_PRICES = {"AAPL": 195.0, "GOOGL": 175.0, "MSFT": 420.0}


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """A fresh database file per test, so db/finally.db is never touched."""
    path = tmp_path / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path


@pytest.fixture
def conn(db_path):
    """An initialized, seeded database inside one open transaction."""
    with transaction() as connection:
        yield connection


@pytest.fixture
def cache():
    """A price cache holding a few known prices."""
    cache = PriceCache()
    now = datetime.now(UTC)
    cache.apply([Quote(ticker=t, price=p, timestamp=now) for t, p in SEEDED_PRICES.items()])
    return cache


@pytest.fixture
def fake_trade():
    """Stands in for app.portfolio.execute_trade: fills at the seeded price."""

    def execute(cache: PriceCache, ticker: str, side: str, quantity: float) -> TradeResult:
        if ticker not in SEEDED_PRICES:
            raise TradeError(f"No price available for {ticker}")
        trade = Trade(
            id=new_id(),
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=SEEDED_PRICES[ticker],
            executed_at=datetime.now(UTC).isoformat(),
        )
        return TradeResult(trade=trade, cash_balance=10_000.0, position=None)

    return execute
