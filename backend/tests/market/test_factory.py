from app.market.factory import create_source
from app.market.massive import MassiveSource
from app.market.simulator import SimulatorSource


def test_no_api_key_selects_simulator(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    source = create_source()
    assert isinstance(source, SimulatorSource)


def test_empty_api_key_selects_simulator(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "")
    source = create_source()
    assert isinstance(source, SimulatorSource)


def test_whitespace_only_api_key_selects_simulator(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "   ")
    source = create_source()
    assert isinstance(source, SimulatorSource)


def test_real_api_key_selects_massive(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "a-real-key")
    source = create_source()
    assert isinstance(source, MassiveSource)


def test_default_poll_interval_is_fifteen_seconds(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "a-real-key")
    monkeypatch.delenv("MARKET_POLL_INTERVAL", raising=False)
    source = create_source()
    assert source.poll_interval == 15.0


def test_custom_poll_interval_is_respected(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "a-real-key")
    monkeypatch.setenv("MARKET_POLL_INTERVAL", "5")
    source = create_source()
    assert source.poll_interval == 5.0
