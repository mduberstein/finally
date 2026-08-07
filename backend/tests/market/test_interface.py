import httpx
import pytest

from app.market.massive import BASE_URL, MassiveSource
from app.market.models import Quote
from app.market.simulator import SimulatorSource


def _massive_source() -> MassiveSource:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "tickers": [{"ticker": t, "lastTrade": {"p": 100.0}} for t in ["AAPL", "GOOGL"]],
            },
        )

    client = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return MassiveSource(api_key="k", client=client)


SOURCES = [
    pytest.param(lambda: SimulatorSource(seed=1), id="simulator"),
    pytest.param(_massive_source, id="massive"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("make_source", SOURCES)
async def test_fetch_returns_quote_objects(make_source):
    source = make_source()
    quotes = await source.fetch(["AAPL", "GOOGL"])

    assert all(isinstance(q, Quote) for q in quotes)
    await source.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("make_source", SOURCES)
async def test_fetch_empty_ticker_list_never_raises(make_source):
    source = make_source()
    quotes = await source.fetch([])
    assert quotes == []
    await source.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("make_source", SOURCES)
async def test_source_declares_name_and_poll_interval(make_source):
    source = make_source()
    assert isinstance(source.name, str) and source.name
    assert source.poll_interval > 0
    await source.aclose()


@pytest.mark.asyncio
async def test_simulator_tolerates_unknown_symbols():
    source = SimulatorSource(seed=1)
    quotes = await source.fetch(["NOT-A-REAL-TICKER"])
    assert len(quotes) == 1
    assert quotes[0].price > 0
