from starlette.testclient import TestClient

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
