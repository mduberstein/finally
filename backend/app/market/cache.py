"""In-memory store of the latest and previous price per ticker."""

from collections.abc import Iterable

from .models import PriceUpdate, Quote


class PriceCache:
    """In-memory store of the latest and previous price per ticker.

    The sole component that remembers a previous price and derives
    direction, so two data sources can never disagree about "did it go up."
    No lock is needed: a single feed task is the only writer, and asyncio
    gives it uncontended access between awaits.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}

    def apply(self, quotes: Iterable[Quote]) -> list[PriceUpdate]:
        """Record quotes and return updates whose price actually changed."""
        changed = []
        for quote in quotes:
            existing = self._prices.get(quote.ticker)
            previous = existing.price if existing else quote.price
            update = PriceUpdate(
                ticker=quote.ticker,
                price=quote.price,
                previous_price=previous,
                timestamp=quote.timestamp,
            )
            self._prices[quote.ticker] = update
            if existing is None or update.price != previous:
                changed.append(update)
        return changed

    def get(self, ticker: str) -> PriceUpdate | None:
        return self._prices.get(ticker)

    def snapshot(self) -> list[PriceUpdate]:
        """Everything currently known — sent to each new SSE subscriber."""
        return list(self._prices.values())
