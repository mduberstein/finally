"""Mock mode is deterministic and its phrasing is a contract with the E2E suite."""

import pytest

from app.llm.mock import NO_ACTION_MESSAGE, mock_reply


def test_buy_request_returns_a_trade():
    reply = mock_reply("buy 10 shares of AAPL")
    assert reply.message == "Mock mode: buying 10 AAPL at the market price."
    assert len(reply.trades) == 1
    trade = reply.trades[0]
    assert (trade.ticker, trade.side, trade.quantity) == ("AAPL", "buy", 10.0)
    assert reply.watchlist_changes == []


def test_sell_request_returns_a_trade():
    reply = mock_reply("sell 4 TSLA")
    assert reply.message == "Mock mode: selling 4 TSLA at the market price."
    trade = reply.trades[0]
    assert (trade.ticker, trade.side, trade.quantity) == ("TSLA", "sell", 4.0)


def test_quantity_defaults_to_one_share():
    reply = mock_reply("buy NVDA")
    assert reply.message == "Mock mode: buying 1 NVDA at the market price."
    assert reply.trades[0].quantity == 1.0


def test_fractional_quantity_is_kept():
    reply = mock_reply("buy 2.5 shares of MSFT")
    assert reply.trades[0].quantity == 2.5
    assert reply.message == "Mock mode: buying 2.5 MSFT at the market price."


def test_lower_case_ticker_is_upper_cased():
    assert mock_reply("buy 3 aapl").trades[0].ticker == "AAPL"


def test_watchlist_add():
    reply = mock_reply("add PYPL to the watchlist")
    assert reply.message == "Mock mode: adding PYPL to the watchlist."
    assert reply.trades == []
    change = reply.watchlist_changes[0]
    assert (change.ticker, change.action) == ("PYPL", "add")


def test_watchlist_remove():
    reply = mock_reply("remove NFLX from the watchlist")
    assert reply.message == "Mock mode: removing NFLX from the watchlist."
    change = reply.watchlist_changes[0]
    assert (change.ticker, change.action) == ("NFLX", "remove")


@pytest.mark.parametrize(
    "message",
    ["how is my portfolio doing?", "what is my biggest risk", "hello"],
)
def test_conversational_message_returns_no_actions(message):
    reply = mock_reply(message)
    assert reply.message == NO_ACTION_MESSAGE
    assert reply.trades == []
    assert reply.watchlist_changes == []


def test_same_input_gives_the_same_reply():
    assert mock_reply("buy 10 shares of AAPL") == mock_reply("buy 10 shares of AAPL")
    assert mock_reply("hello") == mock_reply("hello")
