"""Portfolio, trade, and history endpoints against API_CONTRACT.md."""

from .conftest import set_price

PORTFOLIO_FIELDS = {
    "cash_balance",
    "positions_value",
    "total_value",
    "total_unrealized_pnl",
    "total_unrealized_pnl_percent",
    "positions",
}
POSITION_FIELDS = {
    "ticker",
    "quantity",
    "avg_cost",
    "current_price",
    "market_value",
    "unrealized_pnl",
    "unrealized_pnl_percent",
    "weight",
}


def buy(client, ticker: str, quantity: float):
    return client.post(
        "/api/portfolio/trade", json={"ticker": ticker, "quantity": quantity, "side": "buy"}
    )


class TestGetPortfolio:
    def test_a_fresh_account_is_all_cash(self, client):
        body = client.get("/api/portfolio").json()

        assert body == {
            "cash_balance": 10000.0,
            "positions_value": 0.0,
            "total_value": 10000.0,
            "total_unrealized_pnl": 0.0,
            "total_unrealized_pnl_percent": 0.0,
            "positions": [],
        }

    def test_response_carries_exactly_the_contract_fields(self, client, cache):
        buy(client, "AAPL", 10)
        set_price(cache, "AAPL", 200.0)

        body = client.get("/api/portfolio").json()

        assert set(body) == PORTFOLIO_FIELDS
        assert set(body["positions"][0]) == POSITION_FIELDS

    def test_positions_are_valued_at_the_cached_price(self, client, cache):
        buy(client, "AAPL", 10)
        set_price(cache, "AAPL", 200.0)

        position = client.get("/api/portfolio").json()["positions"][0]

        assert position["current_price"] == 200.0
        assert position["market_value"] == 2000.0
        assert position["unrealized_pnl"] == 50.0
        assert position["unrealized_pnl_percent"] == 2.56


class TestTrade:
    def test_a_buy_returns_the_trade_cash_and_position(self, client):
        response = buy(client, "AAPL", 10)
        body = response.json()

        assert response.status_code == 200
        assert set(body) == {"trade", "cash_balance", "position"}
        assert set(body["trade"]) == {
            "id",
            "ticker",
            "side",
            "quantity",
            "price",
            "executed_at",
        }
        assert body["cash_balance"] == 8050.0
        assert body["position"]["quantity"] == 10.0

    def test_ticker_is_upper_cased(self, client):
        assert buy(client, "aapl", 1).json()["trade"]["ticker"] == "AAPL"

    def test_closing_a_position_returns_a_null_position(self, client):
        buy(client, "AAPL", 5)

        body = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "sell"}
        ).json()

        assert body["position"] is None
        assert body["cash_balance"] == 10000.0

    def test_insufficient_cash_is_a_400_with_both_amounts(self, client):
        response = buy(client, "MSFT", 100)

        assert response.status_code == 400
        assert response.json() == {"detail": "Insufficient cash: need $40000.00, have $10000.00"}

    def test_insufficient_shares_is_a_400(self, client):
        buy(client, "AAPL", 3)

        response = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "sell"}
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Insufficient shares: tried to sell 10 AAPL, hold 3"}

    def test_an_unpriced_ticker_is_a_400(self, client):
        response = buy(client, "ZZZZ", 1)

        assert response.status_code == 400
        assert response.json() == {"detail": "No price available for ZZZZ"}

    def test_zero_quantity_is_rejected_by_validation(self, client):
        assert buy(client, "AAPL", 0).status_code == 422

    def test_negative_quantity_is_rejected_by_validation(self, client):
        assert buy(client, "AAPL", -5).status_code == 422

    def test_an_unknown_side_is_rejected_by_validation(self, client):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "short"}
        )

        assert response.status_code == 422

    def test_a_malformed_ticker_is_rejected_by_validation(self, client):
        assert buy(client, "TOOLONG", 1).status_code == 422

    def test_fractional_quantities_are_accepted(self, client):
        body = buy(client, "AAPL", 0.25).json()

        assert body["position"]["quantity"] == 0.25
        assert body["cash_balance"] == 9951.25


class TestHistory:
    def test_is_empty_before_any_trade(self, client):
        assert client.get("/api/portfolio/history").json() == {"snapshots": []}

    def test_every_trade_adds_a_snapshot(self, client):
        buy(client, "AAPL", 1)
        buy(client, "AAPL", 1)

        body = client.get("/api/portfolio/history").json()

        assert len(body["snapshots"]) == 2
        assert set(body["snapshots"][0]) == {"total_value", "recorded_at"}

    def test_snapshots_are_returned_oldest_first(self, client, cache):
        buy(client, "AAPL", 1)
        set_price(cache, "AAPL", 300.0)
        buy(client, "AAPL", 1)

        values = [
            s["total_value"] for s in client.get("/api/portfolio/history").json()["snapshots"]
        ]

        assert values == [10000.0, 10105.0]

    def test_limit_returns_the_newest_n(self, client):
        for _ in range(3):
            buy(client, "AAPL", 1)

        body = client.get("/api/portfolio/history", params={"limit": 2}).json()

        assert len(body["snapshots"]) == 2

    def test_a_zero_limit_is_rejected(self, client):
        assert client.get("/api/portfolio/history", params={"limit": 0}).status_code == 422
