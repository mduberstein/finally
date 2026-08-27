"""End-to-end API tests for the FinAlly backend."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient


@contextmanager
def make_client(tmp_path: Path) -> Iterator[TestClient]:
    """Build a fresh app with isolated sqlite database for each invocation."""
    os.environ["DB_PATH"] = str(tmp_path / "finally.db")
    os.environ["LLM_MOCK"] = "true"
    os.environ.pop("OPENROUTER_API_KEY", None)
    os.environ.pop("MASSIVE_API_KEY", None)

    # Force imports to re-read environment and construct a fresh app state.
    for module in ("app.config", "app.app_state", "app.main", "app.api.app"):
        if module in sys.modules:
            del sys.modules[module]

    from app.main import app  # pylint: disable=import-outside-toplevel

    with TestClient(app) as client:
        state = client.app.state._finally
        # Seed deterministic baseline prices for initial tests.
        for index, ticker in enumerate(state.database.list_watchlist()):
            state.price_cache.update(ticker, 100.0 + (index % 10))
        yield client


def _parse_response(response, expected_status: int = 200) -> dict[str, Any]:
    assert response.status_code == expected_status
    data = response.json()
    assert isinstance(data, dict) or isinstance(data, list)
    return data


def test_health_and_initialization(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        health = _parse_response(client.get("/api/health"))
        assert health["status"] == "ok"

        portfolio = _parse_response(client.get("/api/portfolio"))
        assert portfolio["user_id"] == "default"
        assert portfolio["cash_balance"] == pytest.approx(10000.0)
        assert portfolio["positions"] == []


def test_watchlist_default_and_updates(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        watchlist = _parse_response(client.get("/api/watchlist"))
        assert len(watchlist) == 10
        tickers = [item["ticker"] for item in watchlist]
        assert "AAPL" in tickers and "NFLX" in tickers

        add_payload = _parse_response(client.post("/api/watchlist", json={"ticker": "NVDA"}), expected_status=200)
        assert add_payload["added"] is False  # already seeded

        add_payload = _parse_response(client.post("/api/watchlist", json={"ticker": "AMAT"}))
        assert add_payload["added"] is True
        watchlist = _parse_response(client.get("/api/watchlist"))
        assert any(item["ticker"] == "AMAT" for item in watchlist)

        remove_payload = _parse_response(client.delete("/api/watchlist/AMAT"))
        assert remove_payload["removed"] is True
        watchlist = _parse_response(client.get("/api/watchlist"))
        assert all(item["ticker"] != "AMAT" for item in watchlist)


def test_trade_buy_and_sell_validation(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        state = client.app.state._finally
        state.price_cache.update("AAPL", 42.0)

        before_portfolio = _parse_response(client.get("/api/portfolio"))
        execute = _parse_response(client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 2}))
        after_portfolio = _parse_response(client.get("/api/portfolio"))

        assert execute["execution"]["trade"]["ticker"] == "AAPL"
        assert execute["execution"]["trade"]["side"] == "buy"
        assert execute["execution"]["trade"]["quantity"] == 2
        assert after_portfolio["cash_balance"] == pytest.approx(before_portfolio["cash_balance"] - 84.0)
        assert any(position["ticker"] == "AAPL" and position["quantity"] > 0 for position in after_portfolio["positions"])

        # Insufficient shares should fail
        sell_response = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "sell", "quantity": 1000})
        assert sell_response.status_code == 400


def test_chat_mock_executes_actions(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        state = client.app.state._finally
        state.price_cache.update("AAPL", 50.0)

        chat_response = _parse_response(
            client.post("/api/chat", json={"message": "Buy 3 AAPL and add NVDA"})
        )
        assert chat_response["message"]
        assert len(chat_response["executed_actions"]) >= 1
        assert any(action["type"] == "trade" for action in chat_response["executed_actions"])
        assert any(action["type"] == "watchlist" for action in chat_response["executed_actions"])

        portfolio = _parse_response(client.get("/api/portfolio"))
        position = next((item for item in portfolio["positions"] if item["ticker"] == "AAPL"), None)
        assert position is not None and position["quantity"] >= 3

        watchlist = _parse_response(client.get("/api/watchlist"))
        assert any(item["ticker"] == "NVDA" for item in watchlist)


def test_frontend_static_mount_tolerates_missing_assets_dir(tmp_path: Path) -> None:
    static_dir = tmp_path / "frontend_out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html><body>FinAlly</body></html>")
    (static_dir / "_next").mkdir()

    os.environ["DB_PATH"] = str(tmp_path / "finally.db")
    os.environ["FINALLY_STATIC_DIR"] = str(static_dir)
    os.environ["LLM_MOCK"] = "true"
    os.environ.pop("OPENROUTER_API_KEY", None)
    os.environ.pop("MASSIVE_API_KEY", None)

    for module in ("app.config", "app.app_state", "app.main", "app.api.app"):
        if module in sys.modules:
            del sys.modules[module]

    from app.main import app  # pylint: disable=import-outside-toplevel

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "FinAlly" in response.text
