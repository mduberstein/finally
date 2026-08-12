"""The app factory: health, static serving, and the lifespan wiring."""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.db import initialize, transaction, watchlist
from app.main import create_app, watched_tickers
from app.market import PriceCache


@pytest.fixture
def static_dir(tmp_path, monkeypatch):
    """A stand-in for the Next.js export, matching FRONTEND_CONTRACT.md's layout."""
    directory = tmp_path / "static"
    (directory / "_next").mkdir(parents=True)
    (directory / "index.html").write_text("<html>FinAlly</html>")
    (directory / "404.html").write_text("<html>not found</html>")
    (directory / "_next" / "app.js").write_text("console.log('bundle')")
    monkeypatch.setattr(main, "STATIC_DIR", directory)
    return directory


class TestHealth:
    def test_reports_ok(self, client):
        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRouters:
    def test_the_chat_router_is_included(self, client):
        """Owned by llm-engineer, mounted here -- this catches an unwired factory."""
        assert client.get("/api/chat/history").status_code != 404


class TestStaticFiles:
    @pytest.fixture
    def client(self, cache, static_dir):
        return TestClient(create_app(cache))

    def test_serves_index_at_the_root(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert "FinAlly" in response.text

    def test_serves_the_asset_bundle(self, client):
        response = client.get("/_next/app.js")

        assert response.status_code == 200
        assert "bundle" in response.text

    def test_an_unknown_path_falls_back_to_the_shell(self, client):
        """The app is a single route, so a deep link or reload must still render it."""
        response = client.get("/positions/AAPL")

        assert response.status_code == 200
        assert "FinAlly" in response.text

    def test_api_routes_take_precedence_over_the_mount(self, client):
        assert client.get("/api/health").json() == {"status": "ok"}

    def test_an_unknown_api_path_is_a_json_404_not_the_shell(self, client):
        """The catch-all must never shadow /api -- a typo'd endpoint stays an API error."""
        response = client.get("/api/nonsense")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert "FinAlly" not in response.text

    def test_an_unknown_stream_path_is_also_a_json_404(self, client):
        response = client.get("/api/stream/nonsense")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")

    def test_the_app_starts_without_a_static_directory(self, cache, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "STATIC_DIR", tmp_path / "absent")

        bare = TestClient(create_app(cache))

        assert bare.get("/api/health").status_code == 200
        assert bare.get("/").status_code == 404


class TestWatchedTickers:
    """The feed's ticker callable, which runs after `initialize()` as the lifespan does."""

    def test_reads_the_current_watchlist(self, db_path):
        initialize()

        assert "AAPL" in watched_tickers()

    def test_picks_up_an_addition_without_a_restart(self, db_path):
        initialize()
        with transaction() as conn:
            watchlist.add(conn, "PYPL")

        assert "PYPL" in watched_tickers()


class TestLifespan:
    def test_starts_and_stops_the_feed_and_recorder(self, db_path):
        app = create_app()

        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 200
            assert isinstance(app.state.prices, PriceCache)

    def test_the_feed_fills_the_cache(self, db_path):
        app = create_app()

        with TestClient(app) as client:
            client.get("/api/health")
            snapshot = app.state.prices.snapshot()

        assert {update.ticker for update in snapshot} == set(watched_tickers())
