import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from app.market.cache import PriceCache
from app.market.feed import MAX_POLL_INTERVAL, MarketFeed
from app.market.interface import MarketDataSource
from app.market.models import Quote


def _quotes(*tickers: str, price: float = 100.0) -> list[Quote]:
    now = datetime.now(UTC)
    return [Quote(t, price, now) for t in tickers]


class FakeSource(MarketDataSource):
    """A source whose behaviour per call is scripted by the test.

    `behaviors` is a queue of either an Exception to raise or a list of
    `Quote`s to return. Once exhausted, `fetch` returns a flat 100.0 quote
    per requested ticker.
    """

    def __init__(self, name="fake", poll_interval=15.0, behaviors=None):
        self.name = name
        self.poll_interval = poll_interval
        self._behaviors = list(behaviors or [])
        self.fetch_calls = 0
        self.closed = False

    async def fetch(self, tickers):
        self.fetch_calls += 1
        if self._behaviors:
            behavior = self._behaviors.pop(0)
            if isinstance(behavior, Exception):
                raise behavior
            return behavior
        return _quotes(*tickers)

    async def aclose(self):
        self.closed = True


def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.massive.com/x")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


class TestMarketFeedResilience:
    async def test_transient_failure_does_not_stop_the_loop(self):
        source = FakeSource(behaviors=[RuntimeError("upstream down")])
        cache = PriceCache()
        feed = MarketFeed(source, cache, lambda: ["AAPL"])

        await feed._tick()  # fails, logged
        await feed._tick()  # recovers

        assert cache.get("AAPL") is not None
        assert source.fetch_calls == 2

    async def test_cached_prices_survive_a_failed_fetch(self):
        source = FakeSource(behaviors=[_quotes("AAPL", price=190.0), RuntimeError("down")])
        cache = PriceCache()
        feed = MarketFeed(source, cache, lambda: ["AAPL"])

        await feed._tick()
        await feed._tick()

        assert cache.get("AAPL").price == 190.0


class TestMarketFeedFallback:
    async def test_401_falls_back_to_fallback_source(self):
        primary = FakeSource(name="massive", behaviors=[_http_error(401)])
        fallback_source = FakeSource(name="simulator")
        cache = PriceCache()
        feed = MarketFeed(
            primary, cache, lambda: ["AAPL"], fallback_factory=lambda: fallback_source
        )

        await feed._tick()

        assert feed.source is fallback_source
        assert primary.closed is True

    async def test_403_falls_back_to_fallback_source(self):
        primary = FakeSource(name="massive", behaviors=[_http_error(403)])
        fallback_source = FakeSource(name="simulator")
        cache = PriceCache()
        feed = MarketFeed(
            primary, cache, lambda: ["AAPL"], fallback_factory=lambda: fallback_source
        )

        await feed._tick()

        assert feed.source is fallback_source

    async def test_fallback_source_is_used_on_the_next_tick(self):
        primary = FakeSource(name="massive", behaviors=[_http_error(401)])
        fallback_source = FakeSource(name="simulator")
        cache = PriceCache()
        feed = MarketFeed(
            primary, cache, lambda: ["AAPL"], fallback_factory=lambda: fallback_source
        )

        await feed._tick()  # falls back
        await feed._tick()  # now fetches from the fallback

        assert cache.get("AAPL") is not None
        assert fallback_source.fetch_calls == 1

    async def test_no_fallback_factory_leaves_source_unchanged(self):
        primary = FakeSource(name="massive", behaviors=[_http_error(401)])
        cache = PriceCache()
        feed = MarketFeed(primary, cache, lambda: ["AAPL"], fallback_factory=None)

        await feed._tick()

        assert feed.source is primary
        assert cache.get("AAPL") is None


class TestMarketFeedBackoff:
    async def test_429_doubles_poll_interval(self):
        primary = FakeSource(name="massive", poll_interval=15.0, behaviors=[_http_error(429)])
        cache = PriceCache()
        feed = MarketFeed(primary, cache, lambda: ["AAPL"])

        await feed._tick()

        assert feed.source.poll_interval == 30.0

    async def test_429_backoff_is_capped(self):
        primary = FakeSource(
            name="massive",
            poll_interval=50.0,
            behaviors=[_http_error(429), _http_error(429)],
        )
        cache = PriceCache()
        feed = MarketFeed(primary, cache, lambda: ["AAPL"])

        await feed._tick()
        await feed._tick()

        assert feed.source.poll_interval == MAX_POLL_INTERVAL

    async def test_successful_fetch_resets_interval_to_base(self):
        primary = FakeSource(name="massive", poll_interval=15.0, behaviors=[_http_error(429)])
        cache = PriceCache()
        feed = MarketFeed(primary, cache, lambda: ["AAPL"])

        await feed._tick()  # backs off to 30s
        assert feed.source.poll_interval == 30.0

        await feed._tick()  # succeeds, resets to base

        assert feed.source.poll_interval == 15.0


class TestMarketFeedLifecycle:
    async def test_start_and_stop(self):
        source = FakeSource(poll_interval=0.01)
        cache = PriceCache()
        feed = MarketFeed(source, cache, lambda: ["AAPL"])

        feed.start()
        await asyncio.sleep(0.03)
        await feed.stop()

        assert source.closed is True
        assert cache.get("AAPL") is not None

    async def test_stop_cancels_the_background_task(self):
        source = FakeSource(poll_interval=0.01)
        cache = PriceCache()
        feed = MarketFeed(source, cache, lambda: ["AAPL"])

        feed.start()
        await asyncio.sleep(0.01)
        task = feed._task
        await feed.stop()

        # stop() only requests cancellation; wait for it to actually land.
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.CancelledError:
            pass

        assert task.cancelled()

    async def test_start_twice_raises(self):
        source = FakeSource(poll_interval=0.01)
        cache = PriceCache()
        feed = MarketFeed(source, cache, lambda: ["AAPL"])

        feed.start()
        with pytest.raises(RuntimeError):
            feed.start()

        await feed.stop()

    async def test_start_after_stop_is_allowed(self):
        source = FakeSource(poll_interval=0.01)
        cache = PriceCache()
        feed = MarketFeed(source, cache, lambda: ["AAPL"])

        feed.start()
        await asyncio.sleep(0.01)
        await feed.stop()

        feed.start()  # does not raise — the previous task is gone
        await asyncio.sleep(0.01)
        await feed.stop()

    async def test_tickers_callable_is_read_each_poll(self):
        source = FakeSource(poll_interval=0.01)
        cache = PriceCache()
        current = ["AAPL"]
        feed = MarketFeed(source, cache, lambda: list(current))

        feed.start()
        await asyncio.sleep(0.015)
        current.append("GOOGL")
        await asyncio.sleep(0.03)
        await feed.stop()

        assert cache.get("GOOGL") is not None
