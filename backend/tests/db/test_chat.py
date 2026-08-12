"""Chat history repository behaviour."""

from app.db import chat


def test_no_messages_on_a_fresh_database(conn):
    assert chat.list_recent(conn) == []


def test_user_message_round_trips_with_no_actions(conn):
    message = chat.append(conn, "user", "buy 10 shares of Apple")
    assert chat.list_recent(conn) == [message]
    assert message.actions == []


def test_assistant_actions_survive_the_json_round_trip(conn):
    actions = [
        {
            "type": "trade",
            "status": "executed",
            "detail": "Bought 10 AAPL @ $195.00",
            "ticker": "AAPL",
        }
    ]
    chat.append(conn, "assistant", "Bought 10 AAPL.", actions)
    assert chat.list_recent(conn)[0].actions == actions


def test_list_recent_is_ascending_in_time(conn):
    chat.append(conn, "user", "first")
    chat.append(conn, "assistant", "second")
    chat.append(conn, "user", "third")
    assert [m.content for m in chat.list_recent(conn)] == ["first", "second", "third"]


def test_the_limit_keeps_the_newest_and_still_returns_them_ascending(conn):
    for content in ("first", "second", "third"):
        chat.append(conn, "user", content)
    assert [m.content for m in chat.list_recent(conn, limit=2)] == ["second", "third"]
