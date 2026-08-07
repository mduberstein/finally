from app.market.factory import create_source
from app.market.massive import MassiveSource
from app.market.simulator import SimulatorSource


class TestCreateSource:
    def test_unset_key_selects_simulator(self, monkeypatch):
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        assert isinstance(create_source(), SimulatorSource)

    def test_empty_key_selects_simulator(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "")
        assert isinstance(create_source(), SimulatorSource)

    def test_whitespace_only_key_selects_simulator(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "   ")
        assert isinstance(create_source(), SimulatorSource)

    def test_real_key_selects_massive(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "sk-live-abc123")
        assert isinstance(create_source(), MassiveSource)

    def test_default_poll_interval_is_15_seconds(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "sk-live-abc123")
        monkeypatch.delenv("MARKET_POLL_INTERVAL", raising=False)
        source = create_source()
        assert source.poll_interval == 15.0

    def test_custom_poll_interval_is_respected(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "sk-live-abc123")
        monkeypatch.setenv("MARKET_POLL_INTERVAL", "5")
        source = create_source()
        assert source.poll_interval == 5.0

    def test_key_with_surrounding_whitespace_is_stripped_but_used(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "  sk-live-abc123  ")
        assert isinstance(create_source(), MassiveSource)
