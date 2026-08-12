"""The structured output the assistant returns, per PLAN.md section 9.

`message` is the only required field. The two action arrays default to empty,
so a purely conversational reply needs nothing else.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradeInstruction(BaseModel):
    """A trade the assistant wants executed."""

    # quantity is bounded by a validator, not Field(gt=0): the latter emits a
    # numeric range keyword that strict structured-output schemas reject.

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float

    @field_validator("ticker")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("quantity")
    @classmethod
    def _positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("quantity must be greater than 0")
        return value


class WatchlistChange(BaseModel):
    """A watchlist modification the assistant wants applied."""

    ticker: str
    action: Literal["add", "remove"]

    @field_validator("ticker")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()


class AssistantReply(BaseModel):
    """The complete structured response from one assistant turn."""

    message: str
    trades: list[TradeInstruction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)
