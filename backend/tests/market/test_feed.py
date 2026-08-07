import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime

import httpx
import pytest

from app.market.cache import PriceCache
from app.market.feed import MAX_BACKOFF_SECONDS, MarketFeed
from app.market.interface import MarketDataSource
from app.market.models import Quote


class ScriptedSource(MarketDataSource):
    """A source whose fetch() outcomes are scripted call-by-call."""

    name = "scripted"
    poll_interval = 0.0

    def __init__(self, outcomes: list) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0
        self.closed = False

    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        self.calls += 1
        outcome = self._outcomes.pop(0) if self._outcomes else []
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def aclose(self) -> None:
        self.closed = True


def quote(ticker: str, price: float) -> Quote:
    return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))


def http_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.mark.asyncio
async def test_feed_survives_transient_failure_and_keeps_cached_prices():
    source = ScriptedSource([[quote("AAPL", 190.0)], RuntimeError("upstream down"), [quote("AAPL", 191.0)]])
    cache = PriceCache()
    feed = MarketFeed(source, cache, lambda: ["AAPL"])

    feed.start()
    await asyncio.sleep(0.05)
    await feed.stop()

    assert cache.get("AAPL") is not None
    assert source.calls >= 2


@pytest.mark.asyncio
async def test_feed_falls_back_to_simulator_on_401():
    fallback_source = ScriptedSource([[quote("AAPL", 100.0)]])
    primary = ScriptedSource([http_status_error(401)])
    cache = PriceCache()
    feed = MarketFeed(primary, cache, lambda: ["AAPL"], fallback_factory=lambda: fallback_source)

    feed.start()
    await asyncio.sleep(0.05)
    await feed.stop()

    assert primary.closed is True
    assert feed._source is fallback_source
    assert cache.get("AAPL") is not None


@pytest.mark.asyncio
async def test_feed_falls_back_to_simulator_on_403():
    fallback_source = ScriptedSource([[quote("AAPL", 100.0)]])
    primary = ScriptedSource([http_status_error(403)])
    cache = PriceCache()
    feed = MarketFeed(primary, cache, lambda: ["AAPL"], fallback_factory=lambda: fallback_source)

    feed.start()
    await asyncio.sleep(0.05)
    await feed.stop()

    assert feed._source is fallback_source


@pytest.mark.asyncio
async def test_feed_without_fallback_factory_keeps_retrying_same_source_on_401():
    primary = ScriptedSource([http_status_error(401), [quote("AAPL", 100.0)]])
    cache = PriceCache()
    feed = MarketFeed(primary, cache, lambda: ["AAPL"])

    feed.start()
    await asyncio.sleep(0.05)
    await feed.stop()

    assert feed._source is primary
    assert cache.get("AAPL") is not None


@pytest.mark.asyncio
async def test_feed_backs_off_on_429():
    primary = ScriptedSource([http_status_error(429)])
    primary.poll_interval = 5.0
    cache = PriceCache()
    feed = MarketFeed(primary, cache, lambda: ["AAPL"])

    feed.start()
    await asyncio.sleep(0.02)
    await feed.stop()

    assert feed._backoff_interval == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_feed_backoff_resets_after_successful_fetch():
    primary = ScriptedSource([http_status_error(429), [quote("AAPL", 100.0)]])
    cache = PriceCache()
    feed = MarketFeed(primary, cache, lambda: ["AAPL"])

    feed.start()
    await asyncio.sleep(0.05)
    await feed.stop()

    assert feed._backoff_interval is None


@pytest.mark.asyncio
async def test_feed_tickers_callable_is_reread_each_tick():
    seen_ticker_args = []

    class RecordingSource(MarketDataSource):
        name = "recording"
        poll_interval = 0.0

        async def fetch(self, tickers):
            seen_ticker_args.append(list(tickers))
            return [quote(t, 1.0) for t in tickers]

    tickers = ["AAPL"]
    feed = MarketFeed(RecordingSource(), PriceCache(), lambda: list(tickers))

    feed.start()
    await asyncio.sleep(0.01)
    tickers.append("GOOGL")
    await asyncio.sleep(0.03)
    await feed.stop()

    assert any("GOOGL" in call for call in seen_ticker_args)


@pytest.mark.asyncio
async def test_stop_closes_the_source():
    source = ScriptedSource([[quote("AAPL", 100.0)]])
    feed = MarketFeed(source, PriceCache(), lambda: ["AAPL"])
    feed.start()
    await asyncio.sleep(0.01)
    await feed.stop()

    assert source.closed is True
