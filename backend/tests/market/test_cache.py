from datetime import UTC, datetime

from app.market.cache import PriceCache
from app.market.models import Quote


def quote(ticker: str, price: float) -> Quote:
    return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))


def test_first_sighting_is_flat_but_reported():
    cache = PriceCache()
    changed = cache.apply([quote("AAPL", 190.0)])

    assert len(changed) == 1
    update = changed[0]
    assert update.direction == "flat"
    assert update.previous_price == update.price == 190.0


def test_price_rise_yields_up_direction():
    cache = PriceCache()
    cache.apply([quote("AAPL", 190.0)])
    changed = cache.apply([quote("AAPL", 195.0)])

    assert len(changed) == 1
    assert changed[0].direction == "up"
    assert changed[0].previous_price == 190.0
    assert changed[0].price == 195.0


def test_price_fall_yields_down_direction():
    cache = PriceCache()
    cache.apply([quote("AAPL", 190.0)])
    changed = cache.apply([quote("AAPL", 185.0)])

    assert changed[0].direction == "down"


def test_unchanged_price_is_not_reported_as_changed():
    cache = PriceCache()
    cache.apply([quote("AAPL", 190.0)])
    changed = cache.apply([quote("AAPL", 190.0)])

    assert changed == []


def test_get_returns_latest_update():
    cache = PriceCache()
    cache.apply([quote("AAPL", 190.0)])
    cache.apply([quote("AAPL", 195.0)])

    update = cache.get("AAPL")
    assert update is not None
    assert update.price == 195.0
    assert update.previous_price == 190.0


def test_get_unknown_ticker_returns_none():
    cache = PriceCache()
    assert cache.get("NOPE") is None


def test_snapshot_returns_everything_known():
    cache = PriceCache()
    cache.apply([quote("AAPL", 190.0), quote("GOOGL", 175.0)])

    snapshot = cache.snapshot()
    tickers = {update.ticker for update in snapshot}
    assert tickers == {"AAPL", "GOOGL"}


def test_snapshot_reflects_latest_apply():
    cache = PriceCache()
    cache.apply([quote("AAPL", 190.0)])
    cache.apply([quote("AAPL", 200.0)])

    snapshot = cache.snapshot()
    assert len(snapshot) == 1
    assert snapshot[0].price == 200.0


def test_change_percent_math_via_cache():
    cache = PriceCache()
    cache.apply([quote("AAPL", 100.0)])
    changed = cache.apply([quote("AAPL", 105.0)])

    assert changed[0].change_percent == 5.0
