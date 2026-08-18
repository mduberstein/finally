"""The LiteLLM/OpenRouter/Cerebras call boundary, the `LLM_MOCK` gate, and
defensive structured-output parsing.

This module never reads, stores, logs, or returns the OpenRouter credential;
LiteLLM resolves it from the process environment (`OPENROUTER_API_KEY`) on
its own.
"""

import logging
import os
import re

from litellm import completion
from pydantic import ValidationError

from .models import PARSE_FALLBACK_MESSAGE, ChatResponse, TradeAction, WatchlistAction

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

_MOCK_REPLY = "Mock response: portfolio and watchlist unchanged."
_PARSE_EXCERPT_LENGTH = 300

_TRADE_PATTERN = re.compile(
    r"\b(buy|sell)\b\s+(\d+)\s+(?:shares?\s+of\s+)?([a-zA-Z]{1,10})\b",
    re.IGNORECASE,
)
_WATCHLIST_ADD_PATTERN = re.compile(
    r"\badd\b\s+([a-zA-Z]{1,10})\b.*\bwatchlist\b", re.IGNORECASE | re.DOTALL
)
_WATCHLIST_REMOVE_PATTERN = re.compile(
    r"\bremove\b\s+([a-zA-Z]{1,10})\b.*\bwatchlist\b", re.IGNORECASE | re.DOTALL
)


def call_llm(messages: list[dict]) -> str:
    """Return the raw model reply as a string.

    When `LLM_MOCK` is `true` (case-insensitively, after stripping), returns
    a deterministic mock reply and never touches `completion` — CHAT-09
    requires zero outbound requests in mock mode. Otherwise issues the exact
    call shape `.claude/skills/cerebras/SKILL.md` mandates.
    """
    if os.getenv("LLM_MOCK", "").strip().lower() == "true":
        return mock_response(messages).model_dump_json()

    response = completion(
        model=MODEL,
        messages=messages,
        response_format=ChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )
    return response.choices[0].message.content


def mock_response(messages: list[dict]) -> ChatResponse:
    """A deterministic `ChatResponse` for `LLM_MOCK=true`.

    Same input yields a byte-identical output on every call — no clock, no
    randomness, no counter, no network. Matches a small set of
    case-insensitive instruction shapes against the last user message: a
    buy or sell of a whole share count in a ticker symbol, or a watchlist
    add or remove of a ticker symbol. Anything that matches nothing returns
    the fixed canned reply with both arrays empty, so CHAT-03, CHAT-04, and
    Phase 5's `LLM_MOCK` E2E suite can drive real actions without a key.
    """
    content = _last_user_content(messages)
    if content:
        trade_match = _TRADE_PATTERN.search(content)
        if trade_match:
            side = trade_match.group(1).lower()
            quantity = int(trade_match.group(2))
            ticker = trade_match.group(3).upper()
            return ChatResponse(
                message=f"Mock: {side} {quantity} {ticker}.",
                trades=[TradeAction(ticker=ticker, side=side, quantity=quantity)],
            )

        add_match = _WATCHLIST_ADD_PATTERN.search(content)
        if add_match:
            ticker = add_match.group(1).upper()
            return ChatResponse(
                message=f"Mock: added {ticker} to the watchlist.",
                watchlist_changes=[WatchlistAction(ticker=ticker, action="add")],
            )

        remove_match = _WATCHLIST_REMOVE_PATTERN.search(content)
        if remove_match:
            ticker = remove_match.group(1).upper()
            return ChatResponse(
                message=f"Mock: removed {ticker} from the watchlist.",
                watchlist_changes=[WatchlistAction(ticker=ticker, action="remove")],
            )

    return ChatResponse(message=_MOCK_REPLY)


def _last_user_content(messages: list[dict]) -> str:
    for entry in reversed(messages):
        if entry.get("role") == "user":
            return entry.get("content", "")
    return ""


def parse_response(raw: str | None) -> ChatResponse:
    """Parse a raw model reply into a `ChatResponse`, defensively.

    A pure function taking a string and returning a model, deliberately
    separated from `call_llm` so TEST-02 can exercise it with fixtures and
    no LiteLLM involvement. `gpt-oss-120b` has documented cases on other
    inference backends of leaking reasoning text alongside or instead of
    the structured payload; a leaked-reasoning response degrades to the
    fallback message rather than propagating as a 500. A `None` reply
    (refusal, content filter, or transient provider hiccup) is handled the
    same way rather than raising `TypeError` out of `model_validate_json`.
    """
    if not isinstance(raw, str):
        logger.warning("chat response was not a string: %r", type(raw).__name__)
        return ChatResponse(message=PARSE_FALLBACK_MESSAGE)
    try:
        return ChatResponse.model_validate_json(raw)
    except (ValidationError, ValueError):
        excerpt = raw[:_PARSE_EXCERPT_LENGTH]
        logger.warning("chat response failed to parse; raw excerpt: %r", excerpt)
        return ChatResponse(message=PARSE_FALLBACK_MESSAGE)
