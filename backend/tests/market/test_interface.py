"""Interface conformance, parametrized over both concrete sources.

Uses httpx.MockTransport for MassiveSource so no test in this module ever
touches the network.
"""

import httpx
import pytest

from app.market.massive import MassiveSource
from app.market.models import Quote
from app.market.simulator import SimulatorSource


def _massive_source() -> MassiveSource:
    def handler(request):
        tickers = request.url.params["tickers"].split(",")
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "tickers": [{"ticker": t, "lastTrade": {"p": 100.0}} for t in tickers],
            },
        )

    client = httpx.AsyncClient(
        base_url="https://api.massive.com", transport=httpx.MockTransport(handler)
    )
    return MassiveSource("test-key", client=client)


@pytest.fixture(params=["simulator", "massive"])
def source(request):
    if request.param == "simulator":
        return SimulatorSource(seed=1)
    return _massive_source()


class TestMarketDataSourceConformance:
    async def test_fetch_returns_quote_objects(self, source):
        quotes = await source.fetch(["AAPL"])
        assert all(isinstance(q, Quote) for q in quotes)

    async def test_fetch_does_not_raise_on_empty_ticker_list(self, source):
        quotes = await source.fetch([])
        assert quotes == []

    async def test_fetch_tolerates_unknown_symbols(self, source):
        quotes = await source.fetch(["NOTAREALTICKERXYZ"])
        assert isinstance(quotes, list)

    async def test_has_name_and_poll_interval(self, source):
        assert isinstance(source.name, str) and source.name
        assert isinstance(source.poll_interval, (int, float))
        assert source.poll_interval > 0

    async def test_aclose_does_not_raise(self, source):
        await source.aclose()
