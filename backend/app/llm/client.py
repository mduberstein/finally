"""One call to the model, one structured reply.

LiteLLM to OpenRouter with Cerebras pinned as the inference provider. No retry
loop and no fallback answer: if the provider errors or the reply will not parse,
the caller turns that into a 503.
"""

import os

from litellm import completion
from pydantic import ValidationError

from .mock import mock_reply
from .schema import AssistantReply

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


class LLMError(Exception):
    """The provider failed, or its response could not be parsed."""


def mock_enabled() -> bool:
    """Whether LLM_MOCK asks for deterministic offline replies."""
    return os.getenv("LLM_MOCK", "").strip().lower() == "true"


def complete(messages: list[dict]) -> AssistantReply:
    """Ask the model for one structured reply, or return the mock in mock mode.

    The last message is the user's new one, which is what mock mode reads.
    """
    if mock_enabled():
        return mock_reply(messages[-1]["content"])

    try:
        response = completion(
            model=MODEL,
            messages=messages,
            response_format=AssistantReply,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
    except Exception as exc:
        raise LLMError(f"LLM provider error: {exc}") from exc

    content = response.choices[0].message.content
    try:
        return AssistantReply.model_validate_json(content)
    except (ValidationError, TypeError) as exc:
        raise LLMError(f"LLM returned an unparseable response: {exc}") from exc
