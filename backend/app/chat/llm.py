"""The LiteLLM/OpenRouter/Cerebras call boundary, the `LLM_MOCK` gate, and
defensive structured-output parsing.

This module never reads, stores, logs, or returns the OpenRouter credential;
LiteLLM resolves it from the process environment (`OPENROUTER_API_KEY`) on
its own.
"""

import logging
import os

from litellm import completion
from pydantic import ValidationError

from .models import PARSE_FALLBACK_MESSAGE, ChatResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

_MOCK_REPLY = "Mock response: portfolio and watchlist unchanged."
_PARSE_EXCERPT_LENGTH = 300


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
    randomness, no counter. Both action lists stay empty in this plan.
    `messages` is accepted but unused here so Plan 03 can extend this to
    react to trade-shaped phrasing (Phase 5's E2E suite) without a
    signature change.
    """
    del messages
    return ChatResponse(message=_MOCK_REPLY)


def parse_response(raw: str) -> ChatResponse:
    """Parse a raw model reply into a `ChatResponse`, defensively.

    A pure function taking a string and returning a model, deliberately
    separated from `call_llm` so TEST-02 can exercise it with fixtures and
    no LiteLLM involvement. `gpt-oss-120b` has documented cases on other
    inference backends of leaking reasoning text alongside or instead of
    the structured payload; a leaked-reasoning response degrades to the
    fallback message rather than propagating as a 500.
    """
    try:
        return ChatResponse.model_validate_json(raw)
    except (ValidationError, ValueError):
        excerpt = raw[:_PARSE_EXCERPT_LENGTH]
        logger.warning("chat response failed to parse; raw excerpt: %r", excerpt)
        return ChatResponse(message=PARSE_FALLBACK_MESSAGE)
