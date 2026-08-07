import httpx
import pytest

from app.market.massive import BASE_URL, SNAPSHOT_PATH, MassiveSource, _extract_price


def make_source(handler) -> MassiveSource:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(base_url=BASE_URL, transport=transport)
    return MassiveSource(api_key="test-key", client=client)


def snapshot_response(tickers: list[dict]) -> httpx.Response:
    return httpx.Response(200, json={"status": "OK", "count": len(tickers), "tickers": tickers})


@pytest.mark.asyncio
async def test_fetch_parses_last_trade_price():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == SNAPSHOT_PATH
        assert request.url.params["tickers"] == "AAPL"
        return snapshot_response(
            [{"ticker": "AAPL", "lastTrade": {"p": 190.42}, "min": {"c": 189.0}}]
        )

    source = make_source(handler)
    quotes = await source.fetch(["AAPL"])

    assert len(quotes) == 1
    assert quotes[0].ticker == "AAPL"
    assert quotes[0].price == 190.42
    await source.aclose()


@pytest.mark.asyncio
async def test_fetch_falls_back_to_prev_day_close_when_others_zeroed():
    def handler(request: httpx.Request) -> httpx.Response:
        return snapshot_response(
            [
                {
                    "ticker": "AAPL",
                    "lastTrade": {"p": 0},
                    "min": {"c": 0},
                    "day": {"c": 0},
                    "prevDay": {"c": 187.65},
                }
            ]
        )

    source = make_source(handler)
    quotes = await source.fetch(["AAPL"])

    assert quotes[0].price == 187.65
    await source.aclose()


@pytest.mark.asyncio
async def test_fetch_falls_back_ladder_order():
    def handler(request: httpx.Request) -> httpx.Response:
        return snapshot_response(
            [
                {
                    "ticker": "AAPL",
                    "min": {"c": 189.0},
                    "day": {"c": 188.0},
                    "prevDay": {"c": 187.0},
                }
            ]
        )

    source = make_source(handler)
    quotes = await source.fetch(["AAPL"])

    assert quotes[0].price == 189.0
    await source.aclose()


@pytest.mark.asyncio
async def test_fetch_drops_tickers_with_no_usable_price():
    def handler(request: httpx.Request) -> httpx.Response:
        return snapshot_response(
            [
                {"ticker": "AAPL", "lastTrade": {"p": 190.0}},
                {"ticker": "DELISTED", "lastTrade": {"p": 0}, "min": {"c": 0}, "day": {"c": 0}, "prevDay": {"c": 0}},
            ]
        )

    source = make_source(handler)
    quotes = await source.fetch(["AAPL", "DELISTED"])

    assert {q.ticker for q in quotes} == {"AAPL"}
    await source.aclose()


@pytest.mark.asyncio
async def test_fetch_empty_tickers_does_not_call_network():
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return snapshot_response([])

    source = make_source(handler)
    quotes = await source.fetch([])

    assert quotes == []
    assert called is False
    await source.aclose()


@pytest.mark.asyncio
async def test_authorization_header_sent():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer super-secret"
        return snapshot_response([])

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(base_url=BASE_URL, transport=transport)
    source = MassiveSource(api_key="super-secret", client=client)
    await source.fetch(["AAPL"])
    await source.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_fetch_raises_http_status_error_on_failure(status):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"status": "ERROR"})

    source = make_source(handler)
    with pytest.raises(httpx.HTTPStatusError):
        await source.fetch(["AAPL"])
    await source.aclose()


def test_extract_price_prefers_last_trade():
    item = {
        "lastTrade": {"p": 190.0},
        "min": {"c": 189.0},
        "day": {"c": 188.0},
        "prevDay": {"c": 187.0},
    }
    assert _extract_price(item) == 190.0


def test_extract_price_returns_none_when_all_absent():
    assert _extract_price({}) is None


def test_source_name_is_massive():
    source = MassiveSource(api_key="k")
    assert source.name == "massive"
