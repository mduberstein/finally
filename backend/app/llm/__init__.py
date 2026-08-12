"""The FinAlly assistant: structured chat with auto-executed trades.

    from app.llm import service

    result = service.respond(price_cache, "buy 10 AAPL")

One model call per turn, one structured reply, actions executed in order.
"""

from .client import LLMError, complete, mock_enabled
from .schema import AssistantReply, TradeInstruction, WatchlistChange

__all__ = [
    "AssistantReply",
    "LLMError",
    "TradeInstruction",
    "WatchlistChange",
    "complete",
    "mock_enabled",
]
