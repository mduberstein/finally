from datetime import UTC, datetime

from app.market.cache import PriceCache
from app.market.models import Quote


def _quote(ticker: str, price: float) -> Quote:
    return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))


class TestPriceCacheApply:
    def test_first_sighting_is_flat(self):
        cache = PriceCache()
        changed = cache.apply([_quote("AAPL", 190.0)])

        assert len(changed) == 1
        update = changed[0]
        assert update.price == 190.0
        assert update.previous_price == 190.0
        assert update.direction == "flat"

    def test_first_sighting_is_still_reported_as_changed(self):
        cache = PriceCache()
        changed = cache.apply([_quote("AAPL", 190.0)])
        assert [u.ticker for u in changed] == ["AAPL"]

    def test_rise_yields_up(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        changed = cache.apply([_quote("AAPL", 195.0)])

        assert len(changed) == 1
        assert changed[0].direction == "up"
        assert changed[0].previous_price == 190.0
        assert changed[0].price == 195.0

    def test_fall_yields_down(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        changed = cache.apply([_quote("AAPL", 185.0)])

        assert changed[0].direction == "down"

    def test_unchanged_price_is_not_reported_as_changed(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        changed = cache.apply([_quote("AAPL", 190.0)])

        assert changed == []

    def test_unchanged_price_still_updates_get(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        cache.apply([_quote("AAPL", 190.0)])

        assert cache.get("AAPL").price == 190.0

    def test_multiple_tickers_independent(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0), _quote("GOOGL", 175.0)])
        changed = cache.apply([_quote("AAPL", 195.0), _quote("GOOGL", 175.0)])

        assert [u.ticker for u in changed] == ["AAPL"]

    def test_change_percent_math(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        changed = cache.apply([_quote("AAPL", 110.0)])

        assert changed[0].change == 10.0
        assert changed[0].change_percent == 10.0


class TestPriceCacheGet:
    def test_unknown_ticker_returns_none(self):
        cache = PriceCache()
        assert cache.get("AAPL") is None

    def test_known_ticker_returns_latest(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        cache.apply([_quote("AAPL", 200.0)])

        assert cache.get("AAPL").price == 200.0


class TestPriceCacheSnapshot:
    def test_empty_cache(self):
        cache = PriceCache()
        assert cache.snapshot() == []

    def test_returns_all_known_tickers(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0), _quote("GOOGL", 175.0)])

        tickers = {u.ticker for u in cache.snapshot()}
        assert tickers == {"AAPL", "GOOGL"}

    def test_reflects_latest_price(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])
        cache.apply([_quote("AAPL", 200.0)])

        snapshot = {u.ticker: u.price for u in cache.snapshot()}
        assert snapshot["AAPL"] == 200.0
