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
from app.portfolio.models import TradeRejected
from app.portfolio.service import execute_trade
from app.watchlist.models import WatchlistRejected
from app.watchlist.service import add_ticker, remove_ticker

from .llm import call_llm, parse_response
from .models import ChatResponse
from .prompt import build_messages, build_portfolio_context

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
    """Run one chat turn: load history and live portfolio context, call the
    model, parse the reply, execute any proposed actions, persist both sides
    of the turn (with the failure explanations appended), and return the
    response payload.
    """
    history = get_recent_messages()
    context = build_portfolio_context(cache)
    messages = build_messages(history, message, context)
    raw = call_llm(messages)
    parsed = parse_response(raw)
    actions, sentences = execute_actions(parsed, cache)

    combined_message = parsed.message
    if sentences:
        combined_message = f"{parsed.message}\n\n" + " ".join(sentences)

    _persist_turn(message, combined_message, actions)
    return {"message": combined_message, "actions": actions}


def execute_actions(response: ChatResponse, cache: PriceCache) -> tuple[list[dict], list[str]]:
    """Run every proposed trade then every proposed watchlist change, one at
    a time, each in its own `try`/`except`. Never batch, never hold a state
    snapshot across actions: `execute_trade` re-reads cash and position
    state on every call inside its own `BEGIN IMMEDIATE` transaction, which
    is what makes two trades in one turn compose correctly.

    Returns the action-payload list (the persisted `chat_messages.actions`
    contract documented in `models.py`) and the list of explanation
    sentences the failures produced.
    """
    actions: list[dict] = []
    sentences: list[str] = []

    for trade in response.trades:
        ticker = trade.ticker.strip().upper()
        side = trade.side
        quantity = trade.quantity

        if quantity <= 0:
            actions.append(
                {
                    "type": "trade",
                    "status": "failed",
                    "ticker": ticker,
                    "side": side,
                    "quantity": quantity,
                    "code": "invalid_trade",
                }
            )
            sentences.append(
                f"Couldn't process the {side} for {ticker}: quantity must be a positive "
                "whole number."
            )
            continue

        try:
            result = execute_trade(ticker, side, quantity, cache)
        except TradeRejected as error:
            actions.append(
                {
                    "type": "trade",
                    "status": "failed",
                    "ticker": ticker,
                    "side": side,
                    "quantity": quantity,
                    "code": error.code,
                }
            )
            sentences.append(rejection_sentence(error))
        else:
            actions.append(
                {
                    "type": "trade",
                    "status": "executed",
                    "ticker": result.ticker,
                    "side": result.side,
                    "quantity": result.quantity,
                    "price": result.price,
                }
            )

    for change in response.watchlist_changes:
        ticker = change.ticker.strip().upper()
        action = change.action

        if action == "add":
            try:
                normalized = add_ticker(change.ticker)
            except WatchlistRejected as error:
                actions.append(
                    {
                        "type": "watchlist",
                        "status": "failed",
                        "ticker": ticker,
                        "action": action,
                        "code": error.code,
                    }
                )
                sentences.append(rejection_sentence(error))
            else:
                actions.append(
                    {
                        "type": "watchlist",
                        "status": "executed",
                        "ticker": normalized,
                        "action": action,
                    }
                )
            continue

        try:
            removed = remove_ticker(change.ticker)
        except WatchlistRejected as error:
            actions.append(
                {
                    "type": "watchlist",
                    "status": "failed",
                    "ticker": ticker,
                    "action": action,
                    "code": error.code,
                }
            )
            sentences.append(rejection_sentence(error))
            continue

        if removed:
            actions.append(
                {
                    "type": "watchlist",
                    "status": "executed",
                    "ticker": ticker,
                    "action": action,
                }
            )
        else:
            # `remove_ticker` is itself idempotent and raises nothing for an
            # absent ticker. Reporting it as executed would make a card
            # claim something that did not happen (04-UI-SPEC.md
            # Discretion resolution 4).
            actions.append(
                {
                    "type": "watchlist",
                    "status": "failed",
                    "ticker": ticker,
                    "action": action,
                    "code": "not_on_watchlist",
                }
            )
            sentences.append(f"{ticker} was not on the watchlist.")

    return actions, sentences


def rejection_sentence(error: TradeRejected | WatchlistRejected) -> str:
    """Map a rejection to one plain-language sentence carrying the exact
    numbers from its `detail()` payload (D-06), mirroring server-side what
    `frontend/lib/trade.ts`'s `tradeErrorMessage` does client-side. Never
    renders a raw exception string into user-facing text.
    """
    detail = error.detail()
    code = detail.get("code")

    if code == "insufficient_cash":
        return (
            f"Couldn't buy {detail['ticker']} — it costs ${detail['cost']:,.2f}, "
            f"only ${detail['cash_balance']:,.2f} available."
        )
    if code == "insufficient_shares":
        return f"Couldn't sell {detail['ticker']} — only {detail['owned']} shares owned."
    if code == "untradable_ticker":
        return f"{detail['ticker']} has no live price and can't be traded."
    if code == "invalid_trade":
        return f"Couldn't process that trade: {detail.get('message', 'invalid request')}."
    if code == "duplicate_ticker":
        return f"{detail['ticker']} is already on the watchlist."
    if code == "watchlist_full":
        return f"Watchlist is full — the limit is {detail['limit']} tickers."
    if code == "invalid_ticker":
        return f"{detail['ticker']!r} is not a valid ticker symbol."
    return "That action couldn't be completed."


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
