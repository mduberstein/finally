"""The chat endpoints against the shapes in API_CONTRACT.md."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat import create_chat_router
from app.llm import service
from app.llm.client import LLMError


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.fixture
def client(db_path, cache):
    app = FastAPI()
    app.include_router(create_chat_router(cache))
    return TestClient(app)


def test_conversational_turn_returns_the_contract_shape(client):
    response = client.post("/api/chat", json={"message": "how is my portfolio?"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"message", "actions", "created_at"}
    assert body["message"] == "Mock mode: no trade or watchlist change requested."
    assert body["actions"] == []


def test_a_buy_returns_an_executed_trade_action(client):
    response = client.post("/api/chat", json={"message": "buy 2 shares of AAPL"})

    assert response.status_code == 200
    assert response.json()["actions"] == [
        {
            "type": "trade",
            "status": "executed",
            "detail": "Bought 2 AAPL @ $195.00",
            "ticker": "AAPL",
        }
    ]


def test_a_rejected_trade_still_returns_200(client):
    response = client.post("/api/chat", json={"message": "buy 500 AAPL"})

    assert response.status_code == 200
    action = response.json()["actions"][0]
    assert action["status"] == "failed"
    assert action["detail"].startswith("Insufficient cash")


def test_a_watchlist_change_is_reported(client):
    response = client.post("/api/chat", json={"message": "add PYPL to the watchlist"})

    assert response.json()["actions"] == [
        {
            "type": "watchlist",
            "status": "executed",
            "detail": "Added PYPL to the watchlist",
            "ticker": "PYPL",
        }
    ]


def test_an_empty_message_is_rejected(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_a_provider_failure_is_a_503(client, monkeypatch):
    def explode(cache, message, trade=None):
        raise LLMError("LLM provider error: upstream 502")

    monkeypatch.setattr(service, "respond", explode)
    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert "upstream 502" in response.json()["detail"]


def test_history_is_empty_before_any_turn(client):
    assert client.get("/api/chat/history").json() == {"messages": []}


def test_history_returns_both_messages_in_order(client):
    client.post("/api/chat", json={"message": "buy 2 shares of AAPL"})

    messages = client.get("/api/chat/history").json()["messages"]

    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert set(messages[0]) == {"role", "content", "actions", "created_at"}
    assert messages[0]["content"] == "buy 2 shares of AAPL"
    assert messages[0]["actions"] == []
    assert messages[1]["actions"][0]["detail"] == "Bought 2 AAPL @ $195.00"


def test_history_respects_its_limit(client):
    client.post("/api/chat", json={"message": "hello"})
    client.post("/api/chat", json={"message": "hello again"})

    assert len(client.get("/api/chat/history", params={"limit": 2}).json()["messages"]) == 2


def test_history_rejects_a_bad_limit(client):
    assert client.get("/api/chat/history", params={"limit": 0}).status_code == 422
