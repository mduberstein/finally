"""Parsing the structured output, from the minimal reply to the full one."""

import pytest
from pydantic import ValidationError

from app.llm.schema import AssistantReply


def test_minimal_reply_defaults_to_no_actions():
    reply = AssistantReply.model_validate_json('{"message": "Your portfolio is fine."}')
    assert reply.message == "Your portfolio is fine."
    assert reply.trades == []
    assert reply.watchlist_changes == []


def test_full_reply_parses_both_action_arrays():
    raw = """
    {
      "message": "Buying Apple and watching PayPal.",
      "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
      "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]
    }
    """
    reply = AssistantReply.model_validate_json(raw)
    assert reply.trades[0].ticker == "AAPL"
    assert reply.trades[0].side == "buy"
    assert reply.trades[0].quantity == 10.0
    assert reply.watchlist_changes[0].ticker == "PYPL"
    assert reply.watchlist_changes[0].action == "add"


def test_tickers_are_upper_cased():
    reply = AssistantReply.model_validate_json(
        '{"message": "ok", "trades": [{"ticker": " aapl ", "side": "sell", "quantity": 1.5}],'
        ' "watchlist_changes": [{"ticker": "pypl", "action": "remove"}]}'
    )
    assert reply.trades[0].ticker == "AAPL"
    assert reply.watchlist_changes[0].ticker == "PYPL"


def test_fractional_quantities_are_allowed():
    reply = AssistantReply.model_validate_json(
        '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 0.25}]}'
    )
    assert reply.trades[0].quantity == 0.25


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        '{"trades": []}',
        '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "hold", "quantity": 1}]}',
        '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 0}]}',
        '{"message": "ok", "watchlist_changes": [{"ticker": "PYPL", "action": "star"}]}',
    ],
)
def test_invalid_payloads_raise_validation_error(raw):
    with pytest.raises(ValidationError):
        AssistantReply.model_validate_json(raw)
