from starlette.testclient import TestClient

from app.db import database
from app.main import app


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("MARKET_SEED", "1")


def _registered_paths(routes) -> set[str]:
    """Recursively collect route paths.

    FastAPI wraps `include_router()` targets in a lazy `_IncludedRouter`
    that has no `.path` of its own — its real routes live under
    `.original_router.routes`, which we descend into.
    """
    paths: set[str] = set()
    for route in routes:
        path = getattr(route, "path", None)
        if path is not None:
            paths.add(path)
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            paths |= _registered_paths(original_router.routes)
    return paths


class TestHealth:
    def test_health_returns_200(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestWatchlist:
    def test_returns_ten_default_tickers(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            response = client.get("/api/watchlist")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 10
        assert [entry["ticker"] for entry in body] == list(database.DEFAULT_TICKERS)


class TestStreamRoute:
    def test_stream_prices_route_registered(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        assert "/api/stream/prices" in _registered_paths(app.routes)


class TestLifespan:
    def test_feed_present_during_context_and_stops_cleanly(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        with TestClient(app) as client:
            assert client.app.state.feed is not None
            assert client.app.state.prices is not None
        # Exiting the context awaits feed.stop(); no assertion needed beyond
        # "this doesn't raise / doesn't emit a pending-task warning".
