"""One chat turn: build context, call the model, execute, persist, return.

Nothing here holds a transaction open across the model call or across trade
execution -- `transaction()` takes a write lock for its duration, and both of
those manage their own.
"""

from app.db import chat, transaction
from app.market import PriceCache
from app.portfolio import execute_trade

from . import actions as action_runner
from .actions import TradeExecutor
from .client import complete
from .context import HISTORY_LIMIT, build_messages


def respond(cache: PriceCache, user_message: str, trade: TradeExecutor | None = None) -> dict:
    """Answer one user message, auto-executing whatever the assistant returned.

    Raises `LLMError` if the provider fails or its reply will not parse; every
    other outcome, including rejected trades, is a successful response.
    """
    with transaction() as conn:
        messages = build_messages(conn, cache, user_message)

    reply = complete(messages)

    with transaction() as conn:
        chat.append(conn, "user", user_message)

    performed = action_runner.execute(cache, reply, trade or execute_trade)

    with transaction() as conn:
        stored = chat.append(conn, "assistant", reply.message, performed)

    return {"message": stored.content, "actions": stored.actions, "created_at": stored.created_at}


def history(limit: int = HISTORY_LIMIT) -> list[dict]:
    """Recent conversation in ascending time order, shaped for the API contract."""
    with transaction() as conn:
        messages = chat.list_recent(conn, limit=limit)
    return [
        {
            "role": message.role,
            "content": message.content,
            "actions": message.actions,
            "created_at": message.created_at,
        }
        for message in messages
    ]
