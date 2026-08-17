import time

from starlette.testclient import TestClient

from app.main import app


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("MARKET_SEED", "1")


class TestGetPortfolio:
    def test_fresh_database_returns_starting_cash(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.get("/api/portfolio")

        assert response.status_code == 200
        body = response.json()
        assert body["cash_balance"] == 10000.0
        assert body["total_value"] == 10000.0
        assert body["positions"] == []


class TestPostTrade:
    def test_valid_buy_returns_fill_price_and_post_trade_cash(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            # Wait for the simulator feed to populate the cache with a price.
            for _ in range(50):
                if client.app.state.prices.snapshot():
                    break
                time.sleep(0.05)
            tickers = [update.ticker for update in client.app.state.prices.snapshot()]
            assert tickers, "expected the simulator feed to have populated the cache"
            ticker = tickers[0]

            response = client.post(
                "/api/portfolio/trade",
                json={"ticker": ticker, "side": "buy", "quantity": 1},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["ticker"] == ticker
        assert "price" in body
        assert "cash_balance" in body

    def test_zero_quantity_returns_422(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "side": "buy", "quantity": 0},
            )
        assert response.status_code == 422

    def test_negative_quantity_returns_422(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "side": "buy", "quantity": -5},
            )
        assert response.status_code == 422

    def test_fractional_quantity_returns_422(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "side": "buy", "quantity": 1.5},
            )
        assert response.status_code == 422


class TestTradeRejectionMapping:
    def test_sell_of_unowned_ticker_returns_400_insufficient_shares(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            for _ in range(50):
                if client.app.state.prices.snapshot():
                    break
                time.sleep(0.05)
            ticker = client.app.state.prices.snapshot()[0].ticker

            response = client.post(
                "/api/portfolio/trade",
                json={"ticker": ticker, "side": "sell", "quantity": 1},
            )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "insufficient_shares"

    def test_unaffordable_buy_returns_400_insufficient_cash(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            for _ in range(50):
                if client.app.state.prices.snapshot():
                    break
                time.sleep(0.05)
            ticker = client.app.state.prices.snapshot()[0].ticker

            response = client.post(
                "/api/portfolio/trade",
                json={"ticker": ticker, "side": "buy", "quantity": 10_000_000},
            )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "insufficient_cash"

    def test_untradable_ticker_returns_400_untradable_ticker(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post(
                "/api/portfolio/trade",
                json={"ticker": "ZZZZ", "side": "buy", "quantity": 1},
            )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "untradable_ticker"

    def test_non_numeric_quantity_returns_422(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "side": "buy", "quantity": "many"},
            )

        assert response.status_code == 422


class TestTradeRequestModel:
    def test_model_fields_has_no_price_key(self):
        from app.portfolio.routes import TradeRequest

        assert "price" not in TradeRequest.model_fields


class TestGetPortfolioHistory:
    def test_fresh_database_returns_200_and_empty_array(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.get("/api/portfolio/history")

        assert response.status_code == 200
        assert response.json() == []

    def test_after_one_trade_returns_200_and_array_of_length_one_with_total_value_and_recorded_at(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            for _ in range(50):
                if client.app.state.prices.snapshot():
                    break
                time.sleep(0.05)
            ticker = client.app.state.prices.snapshot()[0].ticker

            client.post(
                "/api/portfolio/trade",
                json={"ticker": ticker, "side": "buy", "quantity": 1},
            )

            response = client.get("/api/portfolio/history")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert "total_value" in body[0]
        assert "recorded_at" in body[0]
