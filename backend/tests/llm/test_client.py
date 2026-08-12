"""The LiteLLM call, its failure modes, and the mock-mode switch."""

from types import SimpleNamespace

import pytest

from app.llm import client
from app.llm.client import EXTRA_BODY, MODEL, LLMError, complete, mock_enabled
from app.llm.schema import AssistantReply

MESSAGES = [{"role": "user", "content": "buy 10 AAPL"}]


def _response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture(autouse=True)
def _no_mock(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)


def test_calls_the_model_with_cerebras_pinned(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _response('{"message": "Done."}')

    monkeypatch.setattr(client, "completion", fake_completion)
    reply = complete(MESSAGES)

    assert reply.message == "Done."
    assert captured["model"] == MODEL
    assert captured["extra_body"] == EXTRA_BODY
    assert captured["response_format"] is AssistantReply
    assert captured["messages"] == MESSAGES


def test_provider_error_becomes_llm_error(monkeypatch):
    def fake_completion(**kwargs):
        raise RuntimeError("upstream 502")

    monkeypatch.setattr(client, "completion", fake_completion)
    with pytest.raises(LLMError, match="upstream 502"):
        complete(MESSAGES)


def test_malformed_json_becomes_llm_error(monkeypatch):
    monkeypatch.setattr(client, "completion", lambda **kwargs: _response("i am not json"))
    with pytest.raises(LLMError, match="unparseable"):
        complete(MESSAGES)


def test_missing_content_becomes_llm_error(monkeypatch):
    monkeypatch.setattr(client, "completion", lambda **kwargs: _response(None))
    with pytest.raises(LLMError, match="unparseable"):
        complete(MESSAGES)


def test_mock_mode_never_calls_the_provider(monkeypatch):
    def explode(**kwargs):
        raise AssertionError("the provider must not be called in mock mode")

    monkeypatch.setattr(client, "completion", explode)
    monkeypatch.setenv("LLM_MOCK", "true")
    reply = complete(MESSAGES)
    assert reply.trades[0].ticker == "AAPL"


@pytest.mark.parametrize(
    ("value", "expected"), [("true", True), ("TRUE", True), ("false", False), ("", False)]
)
def test_mock_enabled_reads_the_env_var(monkeypatch, value, expected):
    monkeypatch.setenv("LLM_MOCK", value)
    assert mock_enabled() is expected


def test_mock_disabled_when_unset(monkeypatch):
    assert mock_enabled() is False
