"""Auto-execution: one entry per attempt, and a failure never stops the rest."""

from app.db import transaction, watchlist
from app.llm.actions import execute
from app.llm.schema import AssistantReply
from app.portfolio import TradeError


def _reply(**kwargs) -> AssistantReply:
    return AssistantReply(message="ok", **kwargs)


def _watched(ticker: str) -> bool:
    with transaction() as conn:
        return watchlist.exists(conn, ticker)


def test_no_actions_returns_an_empty_list(db_path, cache, fake_trade):
    assert execute(cache, _reply(), fake_trade) == []


def test_executed_buy_is_recorded(db_path, cache, fake_trade):
    reply = _reply(trades=[{"ticker": "AAPL", "side": "buy", "quantity": 10}])

    assert execute(cache, reply, fake_trade) == [
        {
            "type": "trade",
            "status": "executed",
            "detail": "Bought 10 AAPL @ $195.00",
            "ticker": "AAPL",
        }
    ]


def test_executed_sell_is_recorded(db_path, cache, fake_trade):
    reply = _reply(trades=[{"ticker": "MSFT", "side": "sell", "quantity": 2.5}])

    assert execute(cache, reply, fake_trade)[0]["detail"] == "Sold 2.5 MSFT @ $420.00"


def test_rejected_trade_is_recorded_with_the_services_reason(db_path, cache):
    def reject(cache, ticker, side, quantity):
        raise TradeError("Insufficient cash: need $1950.00, have $100.00")

    reply = _reply(trades=[{"ticker": "AAPL", "side": "buy", "quantity": 10}])

    assert execute(cache, reply, reject) == [
        {
            "type": "trade",
            "status": "failed",
            "detail": "Insufficient cash: need $1950.00, have $100.00",
            "ticker": "AAPL",
        }
    ]


def test_a_failed_trade_does_not_stop_the_ones_behind_it(db_path, cache, fake_trade):
    reply = _reply(
        trades=[
            {"ticker": "ZZZZ", "side": "buy", "quantity": 1},
            {"ticker": "AAPL", "side": "buy", "quantity": 2},
        ],
        watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
    )

    actions = execute(cache, reply, fake_trade)

    assert [a["status"] for a in actions] == ["failed", "executed", "executed"]
    assert actions[0]["detail"] == "No price available for ZZZZ"
    assert _watched("PYPL")


def test_watchlist_add_and_remove(db_path, cache, fake_trade):
    reply = _reply(
        watchlist_changes=[
            {"ticker": "PYPL", "action": "add"},
            {"ticker": "NFLX", "action": "remove"},
        ]
    )

    assert execute(cache, reply, fake_trade) == [
        {
            "type": "watchlist",
            "status": "executed",
            "detail": "Added PYPL to the watchlist",
            "ticker": "PYPL",
        },
        {
            "type": "watchlist",
            "status": "executed",
            "detail": "Removed NFLX from the watchlist",
            "ticker": "NFLX",
        },
    ]
    assert _watched("PYPL")
    assert not _watched("NFLX")


def test_adding_a_watched_ticker_fails_without_raising(db_path, cache, fake_trade):
    reply = _reply(watchlist_changes=[{"ticker": "AAPL", "action": "add"}])

    assert execute(cache, reply, fake_trade) == [
        {
            "type": "watchlist",
            "status": "failed",
            "detail": "AAPL is already on the watchlist",
            "ticker": "AAPL",
        }
    ]


def test_removing_an_unwatched_ticker_fails_without_raising(db_path, cache, fake_trade):
    reply = _reply(watchlist_changes=[{"ticker": "PYPL", "action": "remove"}])

    assert execute(cache, reply, fake_trade)[0] == {
        "type": "watchlist",
        "status": "failed",
        "detail": "PYPL is not on the watchlist",
        "ticker": "PYPL",
    }


def test_trades_run_before_watchlist_changes_in_listed_order(db_path, cache, fake_trade):
    reply = _reply(
        trades=[
            {"ticker": "AAPL", "side": "buy", "quantity": 1},
            {"ticker": "GOOGL", "side": "buy", "quantity": 1},
        ],
        watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
    )

    assert [a["ticker"] for a in execute(cache, reply, fake_trade)] == ["AAPL", "GOOGL", "PYPL"]


def test_the_default_executor_is_the_portfolio_trade_service(db_path, cache):
    """No fake: a real buy moves real cash through app.portfolio.execute_trade."""
    from app.db import positions, profile

    reply = _reply(trades=[{"ticker": "AAPL", "side": "buy", "quantity": 2}])

    assert execute(cache, reply)[0]["status"] == "executed"

    with transaction() as conn:
        assert profile.get_cash_balance(conn) == 10_000.0 - 2 * 195.0
        assert positions.get(conn, "AAPL").quantity == 2.0
