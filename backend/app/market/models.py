"""Data models for a market data observation and its derived update."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Quote:
    """A price observation from a market data source."""

    ticker: str
    price: float
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """A quote paired with the previously seen price, ready to stream."""

    ticker: str
    price: float
    previous_price: float
    timestamp: datetime

    @property
    def change(self) -> float:
        return self.price - self.previous_price

    @property
    def change_percent(self) -> float:
        if self.previous_price == 0:
            return 0.0
        return (self.change / self.previous_price) * 100

    @property
    def direction(self) -> str:
        """One of "up", "down", "flat" — drives the frontend flash colour."""
        if self.price > self.previous_price:
            return "up"
        if self.price < self.previous_price:
            return "down"
        return "flat"
