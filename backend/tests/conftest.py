import pytest


@pytest.fixture(autouse=True)
def _clean_market_env(monkeypatch):
    """Every test starts with no market-related environment variables set."""
    for var in ("MASSIVE_API_KEY", "MARKET_POLL_INTERVAL", "MARKET_SEED"):
        monkeypatch.delenv(var, raising=False)
