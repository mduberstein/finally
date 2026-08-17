import time

from starlette.testclient import TestClient

from app.db import database
from app.main import app


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("MARKET_SEED", "1")


class TestPostWatchlist:
    def test_fresh_symbol_returns_200_with_nullable_price_fields(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post("/api/watchlist", json={"ticker": "pypl"})

        assert response.status_code == 200
        body = response.json()
        assert body["ticker"] == "PYPL"
        assert body["price"] is None
        assert body["previous_price"] is None
        assert body["change"] is None
        assert body["change_percent"] is None
        assert body["direction"] is None
        assert body["timestamp"] is None

    def test_duplicate_symbol_returns_400_with_duplicate_code(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            client.post("/api/watchlist", json={"ticker": "PYPL"})
            response = client.post("/api/watchlist", json={"ticker": "PYPL"})

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "duplicate_ticker"

    def test_malformed_symbol_returns_400_and_writes_nothing(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.post("/api/watchlist", json={"ticker": "AA1"})
            watchlist_response = client.get("/api/watchlist")

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_ticker"
        tickers = [entry["ticker"] for entry in watchlist_response.json()]
        assert "AA1" not in tickers

    def test_get_watchlist_includes_added_ticker_with_same_entry_shape(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            client.post("/api/watchlist", json={"ticker": "PYPL"})
            response = client.get("/api/watchlist")

        assert response.status_code == 200
        body = response.json()
        by_ticker = {entry["ticker"]: entry for entry in body}
        assert "PYPL" in by_ticker
        assert set(by_ticker["PYPL"].keys()) == {
            "ticker",
            "price",
            "previous_price",
            "change",
            "change_percent",
            "direction",
            "timestamp",
        }


class TestDeleteWatchlist:
    def test_delete_seeded_ticker_returns_200_removed_true_and_drops_from_get(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            client.post("/api/watchlist", json={"ticker": "PYPL"})
            response = client.delete("/api/watchlist/PYPL")
            watchlist_response = client.get("/api/watchlist")

        assert response.status_code == 200
        assert response.json() == {"ticker": "PYPL", "removed": True}
        tickers = [entry["ticker"] for entry in watchlist_response.json()]
        assert "PYPL" not in tickers

    def test_delete_absent_ticker_returns_200_removed_false(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.delete("/api/watchlist/PYPL")

        assert response.status_code == 200
        assert response.json() == {"ticker": "PYPL", "removed": False}

    def test_delete_malformed_ticker_returns_400_with_invalid_code(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.delete("/api/watchlist/AA1")

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_ticker"

    def test_delete_leaves_positions_and_trades_tables_untouched(self, tmp_path, monkeypatch):
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

            with database.connect() as conn:
                positions_before = [
                    dict(row) for row in conn.execute("SELECT * FROM positions").fetchall()
                ]
                trades_before = [
                    dict(row) for row in conn.execute("SELECT * FROM trades").fetchall()
                ]

            client.delete(f"/api/watchlist/{ticker}")

            with database.connect() as conn:
                positions_after = [
                    dict(row) for row in conn.execute("SELECT * FROM positions").fetchall()
                ]
                trades_after = [
                    dict(row) for row in conn.execute("SELECT * FROM trades").fetchall()
                ]

        assert positions_after == positions_before
        assert trades_after == trades_before
