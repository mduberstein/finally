"""Conversation history with the assistant."""

import json
import sqlite3

from .models import DEFAULT_USER_ID, ChatMessage, new_id, utc_now


def append(
    conn: sqlite3.Connection, role: str, content: str, actions: list[dict] | None = None
) -> ChatMessage:
    """Record a message. `role` is "user" or "assistant"; actions belong to the assistant."""
    message = ChatMessage(
        id=new_id(),
        role=role,
        content=content,
        actions=actions or [],
        created_at=utc_now(),
    )
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            message.id,
            DEFAULT_USER_ID,
            message.role,
            message.content,
            json.dumps(message.actions) if message.actions else None,
            message.created_at,
        ),
    )
    return message


def list_recent(conn: sqlite3.Connection, limit: int = 50) -> list[ChatMessage]:
    """The newest `limit` messages, returned oldest first so the panel reads top to bottom."""
    rows = conn.execute(
        "SELECT id, role, content, actions, created_at FROM chat_messages"
        " WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (DEFAULT_USER_ID, limit),
    ).fetchall()
    return [_message(row) for row in reversed(rows)]


def _message(row: sqlite3.Row) -> ChatMessage:
    return ChatMessage(
        id=row["id"],
        role=row["role"],
        content=row["content"],
        actions=json.loads(row["actions"]) if row["actions"] else [],
        created_at=row["created_at"],
    )
