from contextlib import closing

from app.chat.models import PARSE_FALLBACK_MESSAGE, ChatResponse
from app.chat.service import HISTORY_LIMIT, get_recent_messages, handle_chat_message
from app.db import database
from app.market.cache import PriceCache


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    database.initialize()


def _row_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM chat_messages").fetchone()["n"]


class TestHandleChatMessagePersistence:
    def test_writes_exactly_two_rows_user_then_assistant(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        reply = ChatResponse(message="here's your analysis").model_dump_json()
        monkeypatch.setattr("app.chat.service.call_llm", lambda messages: reply)
        cache = PriceCache()

        handle_chat_message("what's my P&L?", cache)

        with closing(database.connect()) as conn:
            rows = conn.execute(
                "SELECT role, content, actions FROM chat_messages ORDER BY created_at, rowid"
            ).fetchall()

        assert len(rows) == 2
        assert rows[0]["role"] == "user"
        assert rows[0]["content"] == "what's my P&L?"
        assert rows[0]["actions"] is None
        assert rows[1]["role"] == "assistant"
        assert rows[1]["content"] == "here's your analysis"

    def test_returns_dict_with_parsed_message_and_list_actions(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        reply = ChatResponse(message="the reply text").model_dump_json()
        monkeypatch.setattr("app.chat.service.call_llm", lambda messages: reply)
        cache = PriceCache()

        result = handle_chat_message("hi", cache)

        assert result["message"] == "the reply text"
        assert isinstance(result["actions"], list)

    def test_garbage_reply_persists_fallback_and_raises_nothing(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        monkeypatch.setattr("app.chat.service.call_llm", lambda messages: "not valid json")
        cache = PriceCache()

        result = handle_chat_message("hi", cache)

        assert result["message"] == PARSE_FALLBACK_MESSAGE
        with closing(database.connect()) as conn:
            assert _row_count(conn) == 2


class TestGetRecentMessages:
    def test_empty_table_returns_empty_list(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)

        assert get_recent_messages() == []

    def test_returns_chronological_order(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        for reply_text in ("first reply", "second reply"):
            reply = ChatResponse(message=reply_text).model_dump_json()
            monkeypatch.setattr("app.chat.service.call_llm", lambda messages, r=reply: r)
            handle_chat_message(f"turn about {reply_text}", cache)

        messages = get_recent_messages()

        contents = [m["content"] for m in messages]
        assert contents == [
            "turn about first reply",
            "first reply",
            "turn about second reply",
            "second reply",
        ]

    def test_limit_returns_exactly_n_rows_with_newest_last(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        reply = ChatResponse(message="ack").model_dump_json()
        monkeypatch.setattr("app.chat.service.call_llm", lambda messages: reply)
        last_message = None
        for i in range(HISTORY_LIMIT // 2 + 5):
            last_message = f"turn {i}"
            handle_chat_message(last_message, cache)

        messages = get_recent_messages(limit=HISTORY_LIMIT)

        assert len(messages) == HISTORY_LIMIT
        assert messages[-1]["content"] == "ack"
        assert messages[-2]["content"] == last_message

    def test_deserializes_actions_column_null_and_json(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        reply = ChatResponse(message="ok").model_dump_json()
        monkeypatch.setattr("app.chat.service.call_llm", lambda messages: reply)

        handle_chat_message("hi", cache)

        messages = get_recent_messages()
        user_row, assistant_row = messages
        assert user_row["actions"] is None
        assert assistant_row["actions"] == []
        assert isinstance(assistant_row["actions"], list)


class TestMultiTurnHistory:
    def test_two_calls_accumulate_four_rows_and_second_call_sees_first_turn_history(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        captured: list[list[dict]] = []

        def _recorder(messages: list[dict]) -> str:
            captured.append(messages)
            return ChatResponse(message="reply").model_dump_json()

        monkeypatch.setattr("app.chat.service.call_llm", _recorder)

        handle_chat_message("first turn", cache)
        handle_chat_message("second turn", cache)

        with closing(database.connect()) as conn:
            assert _row_count(conn) == 4

        assert len(captured) == 2
        second_call_history_content = [m["content"] for m in captured[1]]
        assert "first turn" in second_call_history_content
        assert "reply" in second_call_history_content
