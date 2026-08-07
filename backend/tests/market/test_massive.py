from datetime import UTC, datetime

import httpx
import pytest

from app.market.massive import MassiveSource, _extract_price


def _client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(
        base_url="https://api.massive.com",
        headers={"Authorization": "Bearer test-key"},
        transport=transport,
    )


def _snapshot_response(tickers: list[dict]) -> httpx.Response:
    return httpx.Response(200, json={"status": "OK", "count": len(tickers), "tickers": tickers})


class TestExtractPrice:
    def test_prefers_last_trade(self):
        item = {
            "lastTrade": {"p": 120.47},
            "min": {"c": 120.42},
            "day": {"c": 120.40},
            "prevDay": {"c": 119.49},
        }
        assert _extract_price(item) == 120.47

    def test_falls_back_to_min_close_when_no_last_trade(self):
        item = {"min": {"c": 120.42}, "day": {"c": 120.40}, "prevDay": {"c": 119.49}}
        assert _extract_price(item) == 120.42

    def test_falls_back_to_day_close(self):
        item = {"day": {"c": 120.40}, "prevDay": {"c": 119.49}}
        assert _extract_price(item) == 120.40

    def test_falls_back_to_prev_day_close_when_day_and_min_are_zeroed(self):
        """The nightly zero-value window: day.c and min.c are 0 between
        3:30 AM and 4:00 AM ET, and on weekends/holidays."""
        item = {
            "lastTrade": {"p": 0},
            "min": {"c": 0},
            "day": {"c": 0},
            "prevDay": {"c": 119.49},
        }
        assert _extract_price(item) == 119.49

    def test_missing_fields_entirely_falls_through(self):
        item = {"prevDay": {"c": 119.49}}
        assert _extract_price(item) == 119.49

    def test_no_usable_price_returns_none(self):
        assert _extract_price({}) is None


class TestMassiveSourceFetch:
    async def test_empty_ticker_list_returns_empty_without_request(self):
        called = False

        def handler(request):
            nonlocal called
            called = True
            return _snapshot_response([])

        source = MassiveSource("test-key", client=_client(handler))
        assert await source.fetch([]) == []
        assert called is False

    async def test_parses_snapshot_into_quotes(self):
        def handler(request):
            assert request.url.params["tickers"] == "AAPL,GOOGL"
            return _snapshot_response(
                [
                    {"ticker": "AAPL", "lastTrade": {"p": 190.5}},
                    {"ticker": "GOOGL", "lastTrade": {"p": 175.25}},
                ]
            )

        source = MassiveSource("test-key", client=_client(handler))
        quotes = await source.fetch(["AAPL", "GOOGL"])

        assert [(q.ticker, q.price) for q in quotes] == [("AAPL", 190.5), ("GOOGL", 175.25)]
        assert all(isinstance(q.timestamp, datetime) for q in quotes)
        assert all(q.timestamp.tzinfo is not None for q in quotes)

    async def test_uses_bearer_auth_header(self):
        def handler(request):
            assert request.headers["Authorization"] == "Bearer test-key"
            return _snapshot_response([])

        source = MassiveSource("test-key", client=_client(handler))
        await source.fetch(["AAPL"])

    async def test_ticker_with_no_usable_price_is_dropped(self):
        def handler(request):
            return _snapshot_response(
                [
                    {"ticker": "AAPL", "lastTrade": {"p": 190.5}},
                    {"ticker": "DELISTED"},
                ]
            )

        source = MassiveSource("test-key", client=_client(handler))
        quotes = await source.fetch(["AAPL", "DELISTED"])

        assert [q.ticker for q in quotes] == ["AAPL"]

    async def test_uses_fallback_ladder_during_zero_value_window(self):
        def handler(request):
            return _snapshot_response(
                [
                    {
                        "ticker": "AAPL",
                        "lastTrade": {"p": 0},
                        "min": {"c": 0},
                        "day": {"c": 0},
                        "prevDay": {"c": 189.0},
                    }
                ]
            )

        source = MassiveSource("test-key", client=_client(handler))
        quotes = await source.fetch(["AAPL"])

        assert quotes[0].price == 189.0

    async def test_name_is_massive(self):
        source = MassiveSource("test-key", client=_client(lambda r: _snapshot_response([])))
        assert source.name == "massive"

    async def test_default_poll_interval(self):
        source = MassiveSource("test-key", client=_client(lambda r: _snapshot_response([])))
        assert source.poll_interval == 15.0

    async def test_custom_poll_interval(self):
        source = MassiveSource(
            "test-key", poll_interval=5.0, client=_client(lambda r: _snapshot_response([]))
        )
        assert source.poll_interval == 5.0


class TestMassiveSourceErrors:
    async def test_401_raises_http_status_error(self):
        source = MassiveSource(
            "bad-key", client=_client(lambda r: httpx.Response(401, json={"status": "ERROR"}))
        )
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await source.fetch(["AAPL"])
        assert exc_info.value.response.status_code == 401

    async def test_403_raises_http_status_error(self):
        source = MassiveSource(
            "free-tier-key",
            client=_client(lambda r: httpx.Response(403, json={"status": "NOT_AUTHORIZED"})),
        )
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await source.fetch(["AAPL"])
        assert exc_info.value.response.status_code == 403

    async def test_429_raises_http_status_error(self):
        source = MassiveSource(
            "test-key", client=_client(lambda r: httpx.Response(429, json={"status": "ERROR"}))
        )
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await source.fetch(["AAPL"])
        assert exc_info.value.response.status_code == 429

    async def test_500_raises_http_status_error(self):
        source = MassiveSource(
            "test-key", client=_client(lambda r: httpx.Response(500, json={"status": "ERROR"}))
        )
        with pytest.raises(httpx.HTTPStatusError):
            await source.fetch(["AAPL"])


class TestMassiveSourceClose:
    async def test_aclose_closes_underlying_client(self):
        source = MassiveSource("test-key", client=_client(lambda r: _snapshot_response([])))
        await source.aclose()
        assert source._client.is_closed
