from datetime import UTC, datetime

from app.market.models import PriceUpdate, Quote


def make_update(price: float, previous_price: float) -> PriceUpdate:
    return PriceUpdate(
        ticker="AAPL",
        price=price,
        previous_price=previous_price,
        timestamp=datetime.now(UTC),
    )


def test_quote_is_immutable():
    quote = Quote(ticker="AAPL", price=190.0, timestamp=datetime.now(UTC))
    try:
        quote.price = 200.0
    except AttributeError:
        pass
    else:
        raise AssertionError("Quote should be frozen")


def test_price_update_change_up():
    update = make_update(price=110.0, previous_price=100.0)
    assert update.change == 10.0
    assert update.direction == "up"


def test_price_update_change_down():
    update = make_update(price=90.0, previous_price=100.0)
    assert update.change == -10.0
    assert update.direction == "down"


def test_price_update_flat():
    update = make_update(price=100.0, previous_price=100.0)
    assert update.change == 0.0
    assert update.direction == "flat"


def test_change_percent():
    update = make_update(price=110.0, previous_price=100.0)
    assert update.change_percent == 10.0


def test_change_percent_zero_previous_price_does_not_divide_by_zero():
    update = make_update(price=10.0, previous_price=0.0)
    assert update.change_percent == 0.0


def test_price_update_is_immutable():
    update = make_update(price=100.0, previous_price=100.0)
    try:
        update.price = 200.0
    except AttributeError:
        pass
    else:
        raise AssertionError("PriceUpdate should be frozen")
