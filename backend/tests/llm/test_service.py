"""One full turn: context, model call, execution, persistence."""

import pytest

from app.db import chat, transaction
from app.llm import client, service
from app.llm.client import LLMError
from app.llm.schema import AssistantReply


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


def _stored_messages(db_path):
    with transaction() as conn:
        return chat.list_recent(conn)


def test_returns_the_contract_shape(db_path, cache, fake_trade):
    result = service.respond(cache, "how is my portfolio?", trade=fake_trade)

    assert set(result) == {"message", "actions", "created_at"}
    assert result["message"] == "Mock mode: no trade or watchlist change requested."
    assert result["actions"] == []
    assert result["created_at"]


def test_a_buy_request_executes_and_reports_the_action(db_path, cache, fake_trade):
    result = service.respond(cache, "buy 10 shares of AAPL", trade=fake_trade)

    assert result["actions"] == [
        {
            "type": "trade",
            "status": "executed",
            "detail": "Bought 10 AAPL @ $195.00",
            "ticker": "AAPL",
        }
    ]


def test_both_messages_are_persisted_in_order(db_path, cache, fake_trade):
    service.respond(cache, "buy 10 shares of AAPL", trade=fake_trade)

    stored = _stored_messages(db_path)
    assert [m.role for m in stored] == ["user", "assistant"]
    assert stored[0].content == "buy 10 shares of AAPL"
    assert stored[0].actions == []
    assert stored[1].actions[0]["detail"] == "Bought 10 AAPL @ $195.00"


def test_a_failed_trade_is_stored_so_the_next_turn_can_explain_it(db_path, cache, fake_trade):
    service.respond(cache, "buy 5 ZZZZ", trade=fake_trade)

    stored = _stored_messages(db_path)
    assert stored[1].actions == [
        {
            "type": "trade",
            "status": "failed",
            "detail": "No price available for ZZZZ",
            "ticker": "ZZZZ",
        }
    ]


def test_history_from_an_earlier_turn_reaches_the_model(db_path, cache, fake_trade, monkeypatch):
    service.respond(cache, "buy 10 shares of AAPL", trade=fake_trade)

    captured = {}

    def fake_complete(messages):
        captured["messages"] = messages
        return AssistantReply(message="ok")

    monkeypatch.setattr(service, "complete", fake_complete)
    service.respond(cache, "what did I just do?", trade=fake_trade)

    contents = [m["content"] for m in captured["messages"]]
    assert "buy 10 shares of AAPL" in contents
    assert (
        "Mock mode: buying 10 AAPL at the market price.\n[actions] executed: Bought 10 AAPL @ $195.00"
        in contents
    )


def test_a_provider_failure_propagates_and_stores_nothing(db_path, cache, fake_trade, monkeypatch):
    def explode(**kwargs):
        raise RuntimeError("upstream 502")

    monkeypatch.setenv("LLM_MOCK", "false")
    monkeypatch.setattr(client, "completion", explode)

    with pytest.raises(LLMError):
        service.respond(cache, "hello", trade=fake_trade)

    assert _stored_messages(db_path) == []


def test_history_returns_ascending_contract_shaped_messages(db_path, cache, fake_trade):
    service.respond(cache, "buy 10 shares of AAPL", trade=fake_trade)

    messages = service.history()

    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert set(messages[0]) == {"role", "content", "actions", "created_at"}
    assert messages[0]["actions"] == []
    assert messages[1]["actions"][0]["status"] == "executed"


def test_history_respects_its_limit(db_path, cache, fake_trade):
    service.respond(cache, "hello", trade=fake_trade)
    service.respond(cache, "hello again", trade=fake_trade)

    assert len(service.history(limit=2)) == 2
