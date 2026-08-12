"""Assembles the message list handed to the model.

One system message with the prompt, one with a snapshot of the portfolio and
watchlist at live prices, then the recent conversation, then the new message.
History is bounded to the last few turns so the prompt cannot grow without limit.
"""

import sqlite3

from app.db import chat, watchlist
from app.market.cache import PriceCache
from app.portfolio import PositionView, build_portfolio

from .prompt import SYSTEM_PROMPT

HISTORY_LIMIT = 20


def build_messages(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_message: str,
    history_limit: int = HISTORY_LIMIT,
) -> list[dict]:
    """The full message list for one turn, oldest context first."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": build_portfolio_context(conn, cache)},
    ]
    for past in chat.list_recent(conn, limit=history_limit):
        messages.append({"role": past.role, "content": _with_actions(past.content, past.actions)})
    messages.append({"role": "user", "content": user_message})
    return messages


def build_portfolio_context(conn: sqlite3.Connection, cache: PriceCache) -> str:
    """A compact plain-text snapshot of cash, positions, value, and watchlist.

    Valued by `app.portfolio.build_portfolio`, the same call `GET /api/portfolio`
    makes, so the numbers the assistant reasons from are the numbers on screen.
    """
    portfolio = build_portfolio(conn, cache)
    lines = [_position_line(position) for position in portfolio.positions]

    return "\n".join(
        [
            "Current portfolio:",
            f"Cash balance: ${portfolio.cash_balance:,.2f}",
            f"Positions value: ${portfolio.positions_value:,.2f}",
            f"Total portfolio value: ${portfolio.total_value:,.2f}",
            f"Total unrealised P&L: {_money(portfolio.total_unrealized_pnl)}"
            f" ({portfolio.total_unrealized_pnl_percent:+.2f}%)",
            "Positions:",
            *(lines or ["  none"]),
            "Watchlist:",
            *(_watchlist_lines(conn, cache) or ["  none"]),
        ]
    )


def _position_line(position: PositionView) -> str:
    """One holding, including its weight so concentration is readable at a glance."""
    return (
        f"  {position.ticker}: {position.quantity:g} shares, avg cost ${position.avg_cost:,.2f}, "
        f"price ${position.current_price:,.2f}, value ${position.market_value:,.2f}, "
        f"unrealised P&L {_money(position.unrealized_pnl)} "
        f"({position.unrealized_pnl_percent:+.2f}%), "
        f"weight {position.weight * 100:.1f}% of the portfolio"
    )


def _money(value: float) -> str:
    """A signed dollar amount, so a loss reads -$80.00 rather than $-80.00."""
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def _watchlist_lines(conn: sqlite3.Connection, cache: PriceCache) -> list[str]:
    lines = []
    for entry in watchlist.list_all(conn):
        update = cache.get(entry.ticker)
        if update is None:
            lines.append(f"  {entry.ticker}: no price yet")
        else:
            lines.append(
                f"  {entry.ticker}: ${update.price:,.2f} ({update.change_percent:+.2f}% last tick)"
            )
    return lines


def _with_actions(content: str, actions: list[dict]) -> str:
    """Past actions ride along in the message text so the model recalls what happened."""
    if not actions:
        return content
    outcomes = "; ".join(f"{a['status']}: {a['detail']}" for a in actions)
    return f"{content}\n[actions] {outcomes}"
