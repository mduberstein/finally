"""The structured-output schema and the persisted action-payload contract.

Persisted `chat_messages.actions` payload contract (Plans 03 and 04 both
build against this, so it is fixed here rather than in either later plan):
one JSON array whose elements are objects with a `type` key of either
`trade` or `watchlist`, a `status` key of either `executed` or `failed`, and
a `ticker` key. A `trade` element additionally carries `side` and
`quantity`, plus `price` when executed or `code` when failed. A `watchlist`
element additionally carries `action`, plus `code` when failed. This plan
always persists an empty array — the executing loop is Plan 03.
"""

from typing import Literal

from pydantic import BaseModel

MAX_MESSAGE_LENGTH = 4000
"""Inbound user-message cap, counted in Python string code points
(`len()` on a `str`) — the only length definition this codebase needs."""

PARSE_FALLBACK_MESSAGE = "Something went wrong processing that — try rephrasing."
"""Returned when the model's response fails to parse as a `ChatResponse`."""


class TradeAction(BaseModel):
    """One LLM-proposed trade. No field-level constraints (`pattern`,
    `format`, `minItems`/`maxItems`) — Cerebras strict mode rejects them on
    the model handed to `response_format`. `int` quantity is D-09's
    whole-share constraint expressed directly in the schema."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: int


class WatchlistAction(BaseModel):
    """One LLM-proposed watchlist change."""

    ticker: str
    action: Literal["add", "remove"]


class ChatResponse(BaseModel):
    """The structured output shape returned by the LLM. Field names come
    from `planning/PLAN.md` section 9 and are not open to renaming."""

    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistAction] = []
