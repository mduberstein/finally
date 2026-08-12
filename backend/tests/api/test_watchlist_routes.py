"""Watchlist CRUD against API_CONTRACT.md."""

from app.db import DEFAULT_TICKERS

ITEM_FIELDS = {
    "ticker",
    "added_at",
    "price",
    "previous_price",
    "change",
    "change_percent",
    "direction",
}


class TestGetWatchlist:
    def test_lists_the_seeded_tickers(self, client):
        body = client.get("/api/watchlist").json()

        assert [item["ticker"] for item in body["tickers"]] == list(DEFAULT_TICKERS)

    def test_a_priced_ticker_carries_every_price_field(self, client):
        items = {item["ticker"]: item for item in client.get("/api/watchlist").json()["tickers"]}

        assert set(items["AAPL"]) == ITEM_FIELDS
        assert items["AAPL"]["price"] == 195.0
        assert items["AAPL"]["direction"] == "flat"

    def test_an_unseen_ticker_reports_null_prices(self, client):
        items = {item["ticker"]: item for item in client.get("/api/watchlist").json()["tickers"]}

        assert items["TSLA"]["price"] is None
        assert items["TSLA"]["change_percent"] is None
        assert items["TSLA"]["direction"] is None


class TestAddTicker:
    def test_returns_201_and_the_new_entry(self, client):
        response = client.post("/api/watchlist", json={"ticker": "PYPL"})

        assert response.status_code == 201
        assert set(response.json()) == ITEM_FIELDS
        assert response.json()["ticker"] == "PYPL"
        assert response.json()["price"] is None

    def test_ticker_is_upper_cased(self, client):
        assert client.post("/api/watchlist", json={"ticker": "pypl"}).json()["ticker"] == "PYPL"

    def test_the_ticker_is_then_watched(self, client):
        client.post("/api/watchlist", json={"ticker": "PYPL"})

        tickers = [item["ticker"] for item in client.get("/api/watchlist").json()["tickers"]]

        assert "PYPL" in tickers

    def test_a_duplicate_is_a_409(self, client):
        response = client.post("/api/watchlist", json={"ticker": "aapl"})

        assert response.status_code == 409
        assert response.json() == {"detail": "AAPL is already on the watchlist"}

    def test_a_non_alphabetic_ticker_is_rejected(self, client):
        assert client.post("/api/watchlist", json={"ticker": "AA-PL"}).status_code == 422

    def test_a_ticker_over_five_letters_is_rejected(self, client):
        assert client.post("/api/watchlist", json={"ticker": "TOOLONG"}).status_code == 422

    def test_an_empty_ticker_is_rejected(self, client):
        assert client.post("/api/watchlist", json={"ticker": ""}).status_code == 422


class TestRemoveTicker:
    def test_returns_204_with_no_body(self, client):
        response = client.delete("/api/watchlist/AAPL")

        assert response.status_code == 204
        assert response.content == b""

    def test_the_ticker_is_then_gone(self, client):
        client.delete("/api/watchlist/AAPL")

        tickers = [item["ticker"] for item in client.get("/api/watchlist").json()["tickers"]]

        assert "AAPL" not in tickers

    def test_lower_case_is_accepted(self, client):
        assert client.delete("/api/watchlist/aapl").status_code == 204

    def test_an_unwatched_ticker_is_a_404(self, client):
        response = client.delete("/api/watchlist/PYPL")

        assert response.status_code == 404
        assert response.json() == {"detail": "PYPL is not on the watchlist"}

    def test_removing_does_not_close_the_position(self, client):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})

        client.delete("/api/watchlist/AAPL")

        positions = client.get("/api/portfolio").json()["positions"]
        assert [p["ticker"] for p in positions] == ["AAPL"]
