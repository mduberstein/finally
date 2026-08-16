import pytest


@pytest.fixture(autouse=True)
def _clean_market_env(monkeypatch):
    """Every test starts with no market-related environment variables set."""
    for var in ("MASSIVE_API_KEY", "MARKET_POLL_INTERVAL", "MARKET_SEED"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _clean_price_cache():
    """`app.main.cache` is a module-level singleton shared by every
    `TestClient(app)` instantiation in this process. Clear it before each
    test so a prior test's prices can't pre-warm a "wait for a fresh price"
    poll or otherwise leak across tests."""
    from app.main import cache

    cache.clear()
    yield
    cache.clear()
