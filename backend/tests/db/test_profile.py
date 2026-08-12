"""Cash balance round trips."""

from app.db import profile
from app.db.seed import STARTING_CASH


def test_seeded_balance_is_the_starting_cash(conn):
    assert profile.get_cash_balance(conn) == STARTING_CASH


def test_set_balance_round_trips(conn):
    profile.set_cash_balance(conn, 8050.25)
    assert profile.get_cash_balance(conn) == 8050.25
