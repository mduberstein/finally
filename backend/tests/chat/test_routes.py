from contextlib import closing

from starlette.testclient import TestClient

from app.chat.models import MAX_MESSAGE_LENGTH
from app.chat.service import HISTORY_LIMIT, handle_chat_message
from app.db import database
from app.main import app
from app.market.cache import PriceCache


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("MARKET_SEED", "1")
    monkeypatch.setenv("LLM_MOCK", "true")


def _row_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM chat_messages").fetchone()["n"]


class TestPostChat:
    def test_well_formed_message_returns_200_with_message_and_actions(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"message": "hello"})

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["message"], str)
        assert isinstance(body["actions"], list)

    def test_empty_message_returns_422_and_writes_no_row(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"message": ""})
            with closing(database.connect()) as conn:
                count = _row_count(conn)

        assert response.status_code == 422
        assert count == 0

    def test_whitespace_only_message_returns_422_and_writes_no_row(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"message": "   "})
            with closing(database.connect()) as conn:
                count = _row_count(conn)

        assert response.status_code == 422
        assert count == 0

    def test_message_one_character_over_cap_returns_422_and_writes_no_row(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post(
                "/api/chat", json={"message": "a" * (MAX_MESSAGE_LENGTH + 1)}
            )
            with closing(database.connect()) as conn:
                count = _row_count(conn)

        assert response.status_code == 422
        assert count == 0


class TestGetChatHistory:
    def test_after_one_post_history_returns_two_entries_user_then_assistant(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            client.post("/api/chat", json={"message": "hello"})
            response = client.get("/api/chat/history")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["role"] == "user"
        assert body[0]["content"]
        assert body[1]["role"] == "assistant"
        assert body[1]["content"]

    def test_history_capped_at_history_limit_with_newest_last(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        database.initialize()
        cache = PriceCache()
        last_message = None
        for i in range(HISTORY_LIMIT // 2 + 5):
            last_message = f"turn {i}"
            handle_chat_message(last_message, cache)

        with TestClient(app) as client:
            response = client.get("/api/chat/history")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == HISTORY_LIMIT
        assert body[-1]["content"] != last_message  # assistant reply is the true last entry
        assert body[-2]["content"] == last_message
