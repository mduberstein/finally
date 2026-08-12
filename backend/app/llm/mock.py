"""Deterministic replies for LLM_MOCK=true. No network, no API key.

The E2E suite asserts on this phrasing, so treat the strings below as a contract
with the integration tester and change them only by agreement.
"""

import re

from .schema import AssistantReply, TradeInstruction, WatchlistChange

NO_ACTION_MESSAGE = "Mock mode: no trade or watchlist change requested."

_TRADE = re.compile(
    r"\b(buy|sell)\b\D{0,20}?(\d+(?:\.\d+)?)?\s*(?:shares?\s+)?(?:of\s+|in\s+)?([A-Za-z]{1,5})\b",
    re.IGNORECASE,
)
_WATCHLIST_ADD = re.compile(
    r"\b(?:add|watch)\b\s+([A-Za-z]{1,5})\b(?:\s+to\s+(?:the\s+)?watchlist)?", re.IGNORECASE
)
_WATCHLIST_REMOVE = re.compile(
    r"\b(?:remove|drop|unwatch)\b\s+([A-Za-z]{1,5})\b(?:\s+from\s+(?:the\s+)?watchlist)?",
    re.IGNORECASE,
)


def mock_reply(user_message: str) -> AssistantReply:
    """The same input always produces the same reply."""
    trade = _TRADE.search(user_message)
    if trade:
        side, raw_quantity, ticker = trade.group(1).lower(), trade.group(2), trade.group(3).upper()
        quantity = float(raw_quantity) if raw_quantity else 1.0
        verb = "buying" if side == "buy" else "selling"
        return AssistantReply(
            message=f"Mock mode: {verb} {quantity:g} {ticker} at the market price.",
            trades=[TradeInstruction(ticker=ticker, side=side, quantity=quantity)],
        )

    added = _WATCHLIST_ADD.search(user_message)
    if added:
        ticker = added.group(1).upper()
        return AssistantReply(
            message=f"Mock mode: adding {ticker} to the watchlist.",
            watchlist_changes=[WatchlistChange(ticker=ticker, action="add")],
        )

    removed = _WATCHLIST_REMOVE.search(user_message)
    if removed:
        ticker = removed.group(1).upper()
        return AssistantReply(
            message=f"Mock mode: removing {ticker} from the watchlist.",
            watchlist_changes=[WatchlistChange(ticker=ticker, action="remove")],
        )

    return AssistantReply(message=NO_ACTION_MESSAGE)
