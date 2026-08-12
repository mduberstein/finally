"""Auto-execution of the actions the assistant returned.

Trades and watchlist changes run in the order the model listed them, with no
confirmation dialog -- deliberate, the money is simulated. Every attempt
produces exactly one entry in the returned list, and a failure never stops the
ones behind it.

Trades go through `app.portfolio.execute_trade`, the same call a manual trade
makes, so they get the same validation. It opens its own transaction, so
nothing here holds one open across it.
"""

from typing import Protocol

from app.db import transaction, watchlist
from app.market import PriceCache
from app.portfolio import TradeError, TradeResult, execute_trade

from .schema import AssistantReply, TradeInstruction, WatchlistChange


class TradeExecutor(Protocol):
    """The trade service's signature, named so tests can substitute it."""

    def __call__(
        self, cache: PriceCache, ticker: str, side: str, quantity: float
    ) -> TradeResult: ...


def execute(
    cache: PriceCache, reply: AssistantReply, trade: TradeExecutor = execute_trade
) -> list[dict]:
    """Run every action, returning one status entry per attempt."""
    actions = [_run_trade(cache, instruction, trade) for instruction in reply.trades]
    actions += [_run_watchlist(change) for change in reply.watchlist_changes]
    return actions


def _run_trade(cache: PriceCache, instruction: TradeInstruction, trade: TradeExecutor) -> dict:
    try:
        result = trade(cache, instruction.ticker, instruction.side, instruction.quantity)
    except TradeError as exc:
        return _action("trade", "failed", exc.detail, instruction.ticker)
    verb = "Bought" if result.trade.side == "buy" else "Sold"
    detail = f"{verb} {result.trade.quantity:g} {result.trade.ticker} @ ${result.trade.price:,.2f}"
    return _action("trade", "executed", detail, result.trade.ticker)


def _run_watchlist(change: WatchlistChange) -> dict:
    ticker = change.ticker
    with transaction() as conn:
        if change.action == "add":
            if watchlist.exists(conn, ticker):
                return _action(
                    "watchlist", "failed", f"{ticker} is already on the watchlist", ticker
                )
            watchlist.add(conn, ticker)
            return _action("watchlist", "executed", f"Added {ticker} to the watchlist", ticker)

        if not watchlist.remove(conn, ticker):
            return _action("watchlist", "failed", f"{ticker} is not on the watchlist", ticker)
        return _action("watchlist", "executed", f"Removed {ticker} from the watchlist", ticker)


def _action(kind: str, status: str, detail: str, ticker: str) -> dict:
    return {"type": kind, "status": status, "detail": detail, "ticker": ticker}
