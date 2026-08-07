import hashlib

import pytest

from app.market.seed_prices import DEFAULT_BETA, DEFAULT_VOLATILITY, PROFILES, profile_for


class TestProfileFor:
    def test_known_ticker_returns_configured_profile(self):
        profile = profile_for("AAPL")
        assert profile == PROFILES["AAPL"]

    def test_unknown_ticker_gets_default_volatility_and_beta(self):
        profile = profile_for("PYPL")
        assert profile.volatility == DEFAULT_VOLATILITY
        assert profile.beta == DEFAULT_BETA

    def test_unknown_ticker_anchor_in_expected_range(self):
        profile = profile_for("PYPL")
        assert 20.0 <= profile.anchor <= 399.99

    def test_unknown_ticker_is_deterministic(self):
        assert profile_for("PYPL") == profile_for("PYPL")

    def test_different_unknown_tickers_get_different_anchors(self):
        assert profile_for("PYPL").anchor != profile_for("AMD").anchor

    def test_matches_hashlib_derivation_not_builtin_hash(self):
        # hashlib.md5 is stable regardless of PYTHONHASHSEED, unlike the
        # built-in hash(), which is salted per-process for strings. Re-derive
        # the expected anchor independently to catch a regression to hash().
        digest = hashlib.md5(b"PYPL").hexdigest()
        expected_anchor = 20.0 + (int(digest[:8], 16) % 38000) / 100.0
        assert profile_for("PYPL").anchor == pytest.approx(expected_anchor)
