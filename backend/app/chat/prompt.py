"""System persona/tone contract, live portfolio context assembly, and
OpenAI-style message-list assembly."""

from app.db import database as db
from app.market.cache import PriceCache
from app.portfolio.service import get_portfolio

SYSTEM_PROMPT = """\
You are FinAlly, an AI trading assistant for a simulated $10,000 portfolio.

Voice: short sentences, lead with numbers, minimal hedging. Be concise and
data-driven.

Behavior: analyze portfolio composition, risk concentration, and P&L when
asked. Suggest trades with reasoning when asked. Act — placing a trade or
editing the watchlist — only when the user asks or explicitly agrees to it
in the same turn. Never volunteer a trade idea or watchlist change
unprompted.

Never include financial-advice disclaimers, risk warnings, or "not
investment advice" hedging of any kind — this is a zero-stakes simulator,
not a real brokerage.

To execute a trade, populate the `trades` array with objects carrying
`ticker`, `side` ("buy" or "sell"), and `quantity`. To change the
watchlist, populate `watchlist_changes` with objects carrying `ticker` and
`action` ("add" or "remove"). Both arrays default to empty. Proposing an
action the user did not ask for or agree to in this turn is wrong.

Trade quantities are always whole numbers of shares, never a dollar amount
converted to a fraction. If the user names a dollar amount instead of a
share count, ask for a share count instead of computing one.

Always respond with the structured object you have been given, with a
`message` field carrying your reply to the user.
"""


def build_portfolio_context(cache: PriceCache) -> str:
    """Render the user's live cash, positions, concentration, and watchlist
    as a compact plain-text block for the system prompt.

    Reads exclusively through `get_portfolio` (cash, positions, totals) and
    `PriceCache` (current prices) — the same sources every prior phase
    established as authoritative. No file path, environment variable,
    credential, or configuration detail is included.
    """
    portfolio = get_portfolio(cache)
    lines = [
        f"Cash balance: ${portfolio['cash_balance']:,.2f}",
        f"Total portfolio value: ${portfolio['total_value']:,.2f}",
    ]

    positions = portfolio["positions"]
    if not positions:
        lines.append("No open positions.")
    else:
        total_value = portfolio["total_value"]
        largest_pct = 0.0
        for position in positions:
            if position["price"] is None:
                lines.append(
                    f"{position['ticker']}: {position['quantity']} shares, "
                    f"avg cost ${position['avg_cost']:,.2f} — unpriced, no live price"
                )
                continue
            market_value = position["quantity"] * position["price"]
            pct = (market_value / total_value * 100) if total_value else 0.0
            largest_pct = max(largest_pct, pct)
            lines.append(
                f"{position['ticker']}: {position['quantity']} shares, "
                f"avg cost ${position['avg_cost']:,.2f}, "
                f"current price ${position['price']:,.2f}, "
                f"unrealized P&L ${position['unrealized_pnl']:,.2f} "
                f"({pct:.1f}% of portfolio)"
            )
        lines.append(f"Largest position concentration: {largest_pct:.1f}% of total value")

    watchlist = db.watchlist_tickers()
    if watchlist:
        watch_parts = []
        for ticker in watchlist:
            update = cache.get(ticker)
            if update is not None:
                watch_parts.append(f"{ticker} ${update.price:,.2f}")
            else:
                watch_parts.append(f"{ticker} (no live price)")
        lines.append("Watchlist: " + ", ".join(watch_parts))
    else:
        lines.append("Watchlist: empty")

    return "\n".join(lines)


def build_messages(
    history: list[dict], user_message: str, context: str | None = None
) -> list[dict]:
    """Assemble the standard OpenAI-style message list: one `system` entry
    (the constant, with `context` appended when supplied), then one entry
    per history row mapping its `role` and `content` straight through, then
    one `user` entry holding the new message.
    """
    system_content = SYSTEM_PROMPT if context is None else f"{SYSTEM_PROMPT}\n\n{context}"
    messages = [{"role": "system", "content": system_content}]
    for row in history:
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages
