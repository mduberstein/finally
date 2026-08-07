import json
from datetime import UTC, datetime

from app.market.cache import PriceCache
from app.market.models import Quote
from app.market.stream import create_stream_router, price_events


def _quote(ticker: str, price: float) -> Quote:
    return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))


class TestPriceEvents:
    async def test_new_subscriber_gets_full_snapshot_first(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0), _quote("GOOGL", 175.0)])

        gen = price_events(cache)
        first = json.loads((await anext(gen))["data"])
        second = json.loads((await anext(gen))["data"])

        emitted_tickers = {first["ticker"], second["ticker"]}
        assert emitted_tickers == {"AAPL", "GOOGL"}
        await gen.aclose()

    async def test_only_changed_tickers_emitted_after_snapshot(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])

        gen = price_events(cache)
        await anext(gen)  # initial snapshot

        cache.apply([_quote("AAPL", 195.0)])
        update = json.loads((await anext(gen))["data"])

        assert update["ticker"] == "AAPL"
        assert update["price"] == 195.0
        assert update["previous_price"] == 190.0
        assert update["direction"] == "up"
        await gen.aclose()

    async def test_event_shape(self):
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])

        gen = price_events(cache)
        event = await anext(gen)

        assert event["event"] == "price"
        data = json.loads(event["data"])
        assert set(data) == {
            "ticker",
            "price",
            "previous_price",
            "change",
            "change_percent",
            "direction",
            "timestamp",
        }
        await gen.aclose()

    async def test_data_is_valid_json_string_not_python_repr(self):
        """Guards against sse-starlette's str(dict) fallback, which would
        emit single-quoted Python repr text that JSON.parse cannot read."""
        cache = PriceCache()
        cache.apply([_quote("AAPL", 190.0)])

        gen = price_events(cache)
        event = await anext(gen)

        assert isinstance(event["data"], str)
        json.loads(event["data"])  # raises if not valid JSON
        await gen.aclose()


class TestCreateStreamRouter:
    def test_registers_expected_route(self):
        router = create_stream_router(PriceCache())
        paths = {route.path for route in router.routes}
        assert "/api/stream/prices" in paths
