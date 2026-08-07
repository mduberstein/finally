from datetime import UTC, datetime

import pytest

from app.market.models import PriceUpdate, Quote


def _update(price: float, previous_price: float) -> PriceUpdate:
    return PriceUpdate(
        ticker="AAPL",
        price=price,
        previous_price=previous_price,
        timestamp=datetime.now(UTC),
    )


class TestQuote:
    def test_is_frozen(self):
        quote = Quote(ticker="AAPL", price=190.0, timestamp=datetime.now(UTC))
        with pytest.raises(AttributeError):
            quote.price = 200.0

    def test_fields(self):
        now = datetime.now(UTC)
        quote = Quote(ticker="AAPL", price=190.0, timestamp=now)
        assert quote.ticker == "AAPL"
        assert quote.price == 190.0
        assert quote.timestamp is now


class TestPriceUpdate:
    def test_is_frozen(self):
        update = _update(price=100.0, previous_price=90.0)
        with pytest.raises(AttributeError):
            update.price = 200.0

    def test_change_up(self):
        update = _update(price=110.0, previous_price=100.0)
        assert update.change == pytest.approx(10.0)
        assert update.direction == "up"

    def test_change_down(self):
        update = _update(price=90.0, previous_price=100.0)
        assert update.change == pytest.approx(-10.0)
        assert update.direction == "down"

    def test_change_flat(self):
        update = _update(price=100.0, previous_price=100.0)
        assert update.change == pytest.approx(0.0)
        assert update.direction == "flat"

    def test_change_percent(self):
        update = _update(price=110.0, previous_price=100.0)
        assert update.change_percent == pytest.approx(10.0)

    def test_change_percent_negative(self):
        update = _update(price=90.0, previous_price=100.0)
        assert update.change_percent == pytest.approx(-10.0)

    def test_change_percent_zero_previous_price_does_not_divide_by_zero(self):
        update = _update(price=5.0, previous_price=0.0)
        assert update.change_percent == 0.0
