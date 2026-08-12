"""The portfolio snapshot and message list handed to the model."""

from app.db import chat, positions, profile, watchlist
from app.llm.context import build_messages, build_portfolio_context
from app.llm.prompt import SYSTEM_PROMPT


def test_context_reports_cash_and_total_value(conn, cache):
    profile.set_cash_balance(conn, 8050.0)
    positions.upsert(conn, "AAPL", 10.0, 190.0)

    context = build_portfolio_context(conn, cache)

    assert "Cash balance: $8,050.00" in context
    assert "Positions value: $1,950.00" in context
    assert "Total portfolio value: $10,000.00" in context


def test_context_reports_position_pnl_at_live_prices(conn, cache):
    positions.upsert(conn, "AAPL", 10.0, 190.0)

    context = build_portfolio_context(conn, cache)

    assert "AAPL: 10 shares" in context
    assert "avg cost $190.00" in context
    assert "price $195.00" in context
    assert "unrealised P&L $50.00 (+2.63%)" in context


def test_context_reports_weight_so_concentration_is_visible(conn, cache):
    profile.set_cash_balance(conn, 0.0)
    positions.upsert(conn, "AAPL", 10.0, 190.0)
    positions.upsert(conn, "MSFT", 1.0, 420.0)

    context = build_portfolio_context(conn, cache)

    assert "weight 82.3% of the portfolio" in context
    assert "weight 17.7% of the portfolio" in context


def test_a_loss_reads_as_a_negative_dollar_amount(conn, cache):
    positions.upsert(conn, "MSFT", 2.0, 460.0)

    context = build_portfolio_context(conn, cache)

    assert "unrealised P&L -$80.00 (-8.70%)" in context
    assert "Total unrealised P&L: -$80.00" in context
    assert "$-" not in context


def test_context_matches_what_the_portfolio_endpoint_reports(conn, cache):
    """The assistant reasons from the same numbers the UI shows."""
    from app.portfolio import build_portfolio

    profile.set_cash_balance(conn, 8050.0)
    positions.upsert(conn, "AAPL", 10.0, 190.0)

    portfolio = build_portfolio(conn, cache)
    context = build_portfolio_context(conn, cache)

    assert f"${portfolio.total_value:,.2f}" in context
    assert f"${portfolio.positions[0].market_value:,.2f}" in context


def test_position_without_a_cached_price_falls_back_to_avg_cost(conn, cache):
    positions.upsert(conn, "ZZZZ", 4.0, 25.0)

    context = build_portfolio_context(conn, cache)

    assert "ZZZZ: 4 shares, avg cost $25.00, price $25.00" in context
    assert "unrealised P&L $0.00 (+0.00%)" in context


def test_context_lists_the_watchlist_with_prices(conn, cache):
    context = build_portfolio_context(conn, cache)

    assert "AAPL: $195.00" in context
    assert "JPM: no price yet" in context


def test_context_says_none_when_nothing_is_held(conn, cache):
    assert "Positions:\n  none" in build_portfolio_context(conn, cache)


def test_messages_start_with_the_prompt_and_end_with_the_user_message(conn, cache):
    messages = build_messages(conn, cache, "how am I doing?")

    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1]["role"] == "system"
    assert "Cash balance" in messages[1]["content"]
    assert messages[-1] == {"role": "user", "content": "how am I doing?"}


def test_history_is_included_oldest_first(conn, cache):
    chat.append(conn, "user", "buy 10 AAPL")
    chat.append(conn, "assistant", "Bought them.")

    messages = build_messages(conn, cache, "and now?")

    assert [m["role"] for m in messages[2:]] == ["user", "assistant", "user"]
    assert messages[2]["content"] == "buy 10 AAPL"
    assert messages[3]["content"] == "Bought them."


def test_history_is_bounded(conn, cache):
    for index in range(10):
        chat.append(conn, "user", f"message {index}")

    messages = build_messages(conn, cache, "latest", history_limit=3)

    history = messages[2:-1]
    assert [m["content"] for m in history] == ["message 7", "message 8", "message 9"]


def test_past_action_outcomes_ride_along_in_the_history(conn, cache):
    chat.append(
        conn,
        "assistant",
        "I tried to buy.",
        [{"type": "trade", "status": "failed", "detail": "Insufficient cash", "ticker": "AAPL"}],
    )

    messages = build_messages(conn, cache, "why did that fail?")

    assert messages[2]["content"] == "I tried to buy.\n[actions] failed: Insufficient cash"


def test_watchlist_says_none_when_empty(conn, cache):
    for entry in watchlist.list_all(conn):
        watchlist.remove(conn, entry.ticker)

    assert "Watchlist:\n  none" in build_portfolio_context(conn, cache)
