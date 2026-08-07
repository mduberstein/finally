from abc import ABC, abstractmethod
from collections.abc import Sequence

from .models import Quote


class MarketDataSource(ABC):
    """Abstract source of current prices for a set of tickers."""

    name: str
    poll_interval: float
    """Seconds the feed should wait between fetches."""

    @abstractmethod
    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        """Return current quotes for the requested tickers.

        Tickers with no available price are omitted rather than raising.
        """

    async def aclose(self) -> None:
        """Release any held resources. Overridden where needed."""
