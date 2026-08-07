"""Live prices from the Massive (formerly Polygon.io) REST snapshot endpoint."""

from collections.abc import Sequence
from datetime import UTC, datetime

import httpx

from .interface import MarketDataSource
from .models import Quote

BASE_URL = "https://api.massive.com"
SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"


class MassiveSource(MarketDataSource):
    """Live prices from the Massive REST snapshot endpoint.

    Uses raw `httpx` rather than the official `massive` client: that client
    is synchronous (built on `urllib3`), and calling it from a FastAPI
    coroutine would block the event loop and stall every open SSE
    connection.
    """

    name = "massive"

    def __init__(
        self,
        api_key: str,
        poll_interval: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.poll_interval = poll_interval
        self._client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )

    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        if not tickers:
            return []

        response = await self._client.get(SNAPSHOT_PATH, params={"tickers": ",".join(tickers)})
        response.raise_for_status()
        payload = response.json()

        now = datetime.now(UTC)
        return [
            Quote(ticker=item["ticker"], price=price, timestamp=now)
            for item in payload.get("tickers", [])
            if (price := _extract_price(item))
        ]

    async def aclose(self) -> None:
        await self._client.aclose()


def _extract_price(item: dict) -> float | None:
    """Most recent usable price.

    Snapshot bars are zeroed nightly at 3:30 AM ET and repopulate from
    4:00 AM, so day and minute closes are 0 outside trading hours. Fall
    through to the previous day's close, which is always populated.
    """
    return (
        item.get("lastTrade", {}).get("p")
        or item.get("min", {}).get("c")
        or item.get("day", {}).get("c")
        or item.get("prevDay", {}).get("c")
    )
