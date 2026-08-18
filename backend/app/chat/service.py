"""HTTP-agnostic chat turn handling and `chat_messages` read/write.

Plain functions with no FastAPI import, matching the rule `app/portfolio`
and `app/watchlist` both document.
"""

import json
import uuid
from contextlib import closing
from datetime import UTC, datetime

from app.db.database import DEFAULT_USER_ID, connect
from app.market.cache import PriceCache

from .llm import call_llm, parse_response
from .prompt import build_messages

HISTORY_LIMIT = 100
"""D-10's cap, resolved to exactly 100 by `04-UI-SPEC.md` Discretion
resolution 3."""


def get_recent_messages(limit: int = HISTORY_LIMIT) -> list[dict]:
    """Return the most recent `limit` chat turns in chronological order.

    Selects newest-first bounded by `limit`, then reverses to ascending
    order — exactly like `get_portfolio_history`. Selecting ascending with
    a LIMIT would return the OLDEST hundred messages, the opposite of what
    D-10 asks for.
    """
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT role, content, actions, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (DEFAULT_USER_ID, limit),
        ).fetchall()
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "actions": json.loads(row["actions"]) if row["actions"] is not None else None,
            "created_at": row["created_at"],
        }
        for row in reversed(rows)
    ]


def handle_chat_message(message: str, cache: PriceCache) -> dict:
    """Run one chat turn: load history, call the model, parse the reply,
    persist both sides of the turn, and return the response payload.

    `cache` is accepted now even though this plan does not read it, so
    Plan 03's portfolio-context builder needs no signature change.
    """
    del cache
    history = get_recent_messages()
    messages = build_messages(history, message)
    raw = call_llm(messages)
    parsed = parse_response(raw)
    actions: list[dict] = []
    _persist_turn(message, parsed.message, actions)
    return {"message": parsed.message, "actions": actions}


def _persist_turn(user_message: str, assistant_message: str, actions: list[dict]) -> None:
    """Write both rows of one chat turn inside a single transaction.

    The user row is inserted first so `ORDER BY created_at, rowid` restores
    the turn in the order it happened.
    """
    now_user = datetime.now(UTC).isoformat()
    with closing(connect()) as conn, conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, 'user', ?, NULL, ?)",
            (uuid.uuid4().hex, DEFAULT_USER_ID, user_message, now_user),
        )
        now_assistant = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, 'assistant', ?, ?, ?)",
            (
                uuid.uuid4().hex,
                DEFAULT_USER_ID,
                assistant_message,
                json.dumps(actions),
                now_assistant,
            ),
        )
