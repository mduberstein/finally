"""The unified market data source contract."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .models import Quote


class MarketDataSource(ABC):
    """Abstract source of current prices for a set of tickers.

    Contract:
      - `fetch` is async and must not block the event loop.
      - `fetch` is stateless with respect to the caller — calling it twice
        with the same tickers is always valid.
      - `fetch` may return fewer quotes than requested. Unknown, delisted, or
        temporarily unavailable tickers are dropped silently. Callers must
        not assume a one-to-one mapping.
      - `fetch` raises only on total failure (network down, auth rejected).
        A partial result is a success.
      - `poll_interval` is advisory and read by the feed.
    """

    name: str
    poll_interval: float

    @abstractmethod
    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        """Return current quotes for the requested tickers."""

    async def aclose(self) -> None:
        """Release any held resources. Overridden where needed."""
        return None
