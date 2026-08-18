from contextlib import closing
from datetime import UTC, datetime

import pytest

from app.chat.models import PARSE_FALLBACK_MESSAGE, ChatResponse, TradeAction, WatchlistAction
from app.chat.service import (
    HISTORY_LIMIT,
    execute_actions,
    get_recent_messages,
    handle_chat_message,
    rejection_sentence,
)
from app.db import database
from app.market.cache import PriceCache
from app.market.models import Quote
from app.portfolio.models import InsufficientCashError, InsufficientSharesError
from app.watchlist.models import WatchlistFullError


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    database.initialize()


def _row_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM chat_messages").fetchone()["n"]


def _quote(ticker: str, price: float) -> Quote:
    return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))


def _table_snapshot(conn) -> dict:
    return {
        "users_profile": [dict(row) for row in conn.execute("SELECT * FROM users_profile")],
        "positions": [dict(row) for row in conn.execute("SELECT * FROM positions")],
        "trades": [dict(row) for row in conn.execute("SELECT * FROM trades")],
        "portfolio_snapshots": [
            dict(row) for row in conn.execute("SELECT * FROM portfolio_snapshots")
        ],
    }


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


class TestExecuteActionsTrades:
    def test_buy_executes_reduces_cash_and_appends_trade_and_snapshot_rows(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        response = ChatResponse(
            message="ok", trades=[TradeAction(ticker="AAPL", side="buy", quantity=2)]
        )

        actions, sentences = execute_actions(response, cache)

        assert sentences == []
        assert len(actions) == 1
        assert actions[0]["type"] == "trade"
        assert actions[0]["status"] == "executed"
        assert actions[0]["price"] == 100.0
        with closing(database.connect()) as conn:
            positions = conn.execute("SELECT * FROM positions").fetchall()
            trades = conn.execute("SELECT * FROM trades").fetchall()
            snapshots = conn.execute("SELECT * FROM portfolio_snapshots").fetchall()
            cash = conn.execute("SELECT cash_balance FROM users_profile").fetchone()
        assert len(positions) == 1
        assert positions[0]["quantity"] == 2
        assert len(trades) == 1
        assert len(snapshots) == 1
        assert cash["cash_balance"] == pytest.approx(10000.0 - 200.0)

    def test_sell_reduces_position_and_returns_cash(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        execute_actions(
            ChatResponse(
                message="ok", trades=[TradeAction(ticker="AAPL", side="buy", quantity=5)]
            ),
            cache,
        )

        actions, sentences = execute_actions(
            ChatResponse(
                message="ok", trades=[TradeAction(ticker="AAPL", side="sell", quantity=3)]
            ),
            cache,
        )

        assert sentences == []
        assert actions[0]["status"] == "executed"
        with closing(database.connect()) as conn:
            position = conn.execute(
                "SELECT quantity FROM positions WHERE ticker='AAPL'"
            ).fetchone()
        assert position["quantity"] == 2


class TestExecuteActionsUnchangedStateOnRefusal:
    def test_unaffordable_buy_leaves_state_untouched_and_reports_exact_numbers(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        with closing(database.connect()) as conn:
            before = _table_snapshot(conn)

        response = ChatResponse(
            message="ok", trades=[TradeAction(ticker="AAPL", side="buy", quantity=1000)]
        )
        actions, sentences = execute_actions(response, cache)

        with closing(database.connect()) as conn:
            after = _table_snapshot(conn)
        assert before == after
        assert actions[0]["status"] == "failed"
        assert actions[0]["code"] == "insufficient_cash"
        assert "100,000.00" in sentences[0]
        assert "10,000.00" in sentences[0]

    def test_oversell_reports_owned_quantity_and_leaves_state_untouched(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        execute_actions(
            ChatResponse(
                message="ok", trades=[TradeAction(ticker="AAPL", side="buy", quantity=2)]
            ),
            cache,
        )
        with closing(database.connect()) as conn:
            before = _table_snapshot(conn)

        response = ChatResponse(
            message="ok", trades=[TradeAction(ticker="AAPL", side="sell", quantity=10)]
        )
        actions, sentences = execute_actions(response, cache)

        with closing(database.connect()) as conn:
            after = _table_snapshot(conn)
        assert before == after
        assert actions[0]["code"] == "insufficient_shares"
        assert "2" in sentences[0]

    def test_untradable_ticker_returns_failed_action_naming_ticker(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        response = ChatResponse(
            message="ok", trades=[TradeAction(ticker="ZZZZ", side="buy", quantity=1)]
        )
        actions, sentences = execute_actions(response, cache)

        assert actions[0]["code"] == "untradable_ticker"
        assert "ZZZZ" in sentences[0]

    def test_zero_quantity_refused_before_execute_trade_is_called(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])

        response = ChatResponse(
            message="ok", trades=[TradeAction(ticker="AAPL", side="buy", quantity=0)]
        )
        actions, sentences = execute_actions(response, cache)

        assert actions[0]["status"] == "failed"
        assert actions[0]["code"] == "invalid_trade"
        with closing(database.connect()) as conn:
            positions = conn.execute("SELECT * FROM positions").fetchall()
        assert positions == []

    def test_negative_quantity_refused_before_execute_trade_is_called(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])

        response = ChatResponse(
            message="ok", trades=[TradeAction(ticker="AAPL", side="buy", quantity=-5)]
        )
        actions, sentences = execute_actions(response, cache)

        assert actions[0]["status"] == "failed"
        assert actions[0]["code"] == "invalid_trade"


class TestExecuteActionsPartialFailure:
    def test_first_succeeds_second_fails_both_reported_exactly_one_cash_delta(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        response = ChatResponse(
            message="ok",
            trades=[
                TradeAction(ticker="AAPL", side="buy", quantity=2),
                TradeAction(ticker="AAPL", side="buy", quantity=1000),
            ],
        )

        actions, sentences = execute_actions(response, cache)

        assert len(actions) == 2
        assert actions[0]["status"] == "executed"
        assert actions[1]["status"] == "failed"
        with closing(database.connect()) as conn:
            cash = conn.execute("SELECT cash_balance FROM users_profile").fetchone()
        assert cash["cash_balance"] == pytest.approx(10000.0 - 200.0)


class TestExecuteActionsWatchlist:
    def test_add_new_ticker_inserts_and_returns_executed(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        response = ChatResponse(
            message="ok", watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")]
        )
        actions, sentences = execute_actions(response, cache)

        assert actions[0]["status"] == "executed"
        assert "PYPL" in database.watchlist_tickers()

    def test_add_duplicate_ticker_in_same_turn_fails_second_and_inserts_once(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        response = ChatResponse(
            message="ok",
            watchlist_changes=[
                WatchlistAction(ticker="PYPL", action="add"),
                WatchlistAction(ticker="PYPL", action="add"),
            ],
        )
        actions, sentences = execute_actions(response, cache)

        assert actions[0]["status"] == "executed"
        assert actions[1]["status"] == "failed"
        assert actions[1]["code"] == "duplicate_ticker"
        assert database.watchlist_tickers().count("PYPL") == 1

    def test_add_ticker_already_on_watchlist_fails_and_inserts_nothing(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        response = ChatResponse(
            message="ok", watchlist_changes=[WatchlistAction(ticker="AAPL", action="add")]
        )
        actions, sentences = execute_actions(response, cache)

        assert actions[0]["status"] == "failed"
        assert actions[0]["code"] == "duplicate_ticker"
        assert database.watchlist_tickers().count("AAPL") == 1

    def test_remove_absent_ticker_changes_nothing_and_reports_non_executed(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        response = ChatResponse(
            message="ok", watchlist_changes=[WatchlistAction(ticker="ZZZZ", action="remove")]
        )
        actions, sentences = execute_actions(response, cache)

        assert actions[0]["status"] == "failed"
        assert "ZZZZ" not in database.watchlist_tickers()


class TestRejectionSentence:
    def test_insufficient_cash_carries_cost_and_cash_balance(self):
        error = InsufficientCashError("AAPL", 500.0, 100.0)

        sentence = rejection_sentence(error)

        assert "500.00" in sentence
        assert "100.00" in sentence
        assert "AAPL" in sentence

    def test_insufficient_shares_carries_owned_quantity(self):
        error = InsufficientSharesError("AAPL", 3)

        sentence = rejection_sentence(error)

        assert "3" in sentence
        assert "AAPL" in sentence

    def test_watchlist_full_carries_limit(self):
        error = WatchlistFullError(50)

        sentence = rejection_sentence(error)

        assert "50" in sentence


class TestActionsPersistedOnAssistantRow:
    def test_reload_restores_executed_and_failed_actions(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0)])
        reply = ChatResponse(
            message="doing it",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=1000)],
        ).model_dump_json()
        monkeypatch.setattr("app.chat.service.call_llm", lambda messages: reply)

        handle_chat_message("buy 1000 AAPL", cache)

        messages = get_recent_messages()
        assistant_row = messages[-1]
        assert assistant_row["actions"][0]["status"] == "failed"
        assert assistant_row["actions"][0]["code"] == "insufficient_cash"
        assert "100,000.00" in assistant_row["content"]
