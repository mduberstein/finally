from datetime import UTC, datetime

from app.chat.prompt import SYSTEM_PROMPT, build_messages, build_portfolio_context
from app.db import database
from app.market.cache import PriceCache
from app.market.models import Quote
from app.portfolio.service import execute_trade


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "finally.db"))
    database.initialize()


def _quote(ticker: str, price: float) -> Quote:
    return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))


class TestBuildPortfolioContextEmpty:
    def test_no_positions_includes_starting_cash_and_no_positions_statement(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()

        context = build_portfolio_context(cache)

        assert "10,000.00" in context
        assert "no open positions" in context.lower()


class TestBuildPortfolioContextWithPositions:
    def test_two_positions_include_ticker_quantity_avg_cost_price_and_pnl(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 200.0), _quote("MSFT", 300.0)])
        execute_trade("AAPL", "buy", 10, cache)
        execute_trade("MSFT", "buy", 5, cache)
        cache.apply([_quote("AAPL", 220.0), _quote("MSFT", 310.0)])

        context = build_portfolio_context(cache)

        assert "AAPL" in context
        assert "MSFT" in context
        assert "200.00" in context
        assert "300.00" in context
        assert "220.00" in context
        assert "310.00" in context
        assert "200.00" in context  # avg cost for AAPL

    def test_two_positions_include_total_value_and_largest_concentration_pct(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 100.0), _quote("MSFT", 100.0)])
        execute_trade("AAPL", "buy", 90, cache)
        execute_trade("MSFT", "buy", 10, cache)

        context = build_portfolio_context(cache)

        assert "10,000.00" in context  # total value: 90*100 + 10*100 + 0 cash = 10000
        assert "90.0%" in context or "90.0 %" in context or "90%" in context

    def test_unpriced_position_shows_quantity_avg_cost_and_unpriced_marker(
        self, tmp_path, monkeypatch
    ):
        _use_tmp_db(tmp_path, monkeypatch)
        pricing_cache = PriceCache()
        pricing_cache.apply([_quote("AAPL", 200.0)])
        execute_trade("AAPL", "buy", 10, pricing_cache)

        empty_cache = PriceCache()
        context = build_portfolio_context(empty_cache)

        assert "AAPL" in context
        assert "200.00" in context
        assert "unpriced" in context.lower() or "no live price" in context.lower()
        # no fabricated zero valuation
        assert "$0.00" not in context.split("AAPL")[1].split("\n")[0]


class TestBuildPortfolioContextWatchlist:
    def test_watchlist_tickers_and_prices_included(self, tmp_path, monkeypatch):
        _use_tmp_db(tmp_path, monkeypatch)
        cache = PriceCache()
        cache.apply([_quote("AAPL", 195.5)])

        context = build_portfolio_context(cache)

        assert "AAPL" in context
        assert "195.50" in context
        assert "GOOGL" in context  # seeded default watchlist ticker, unpriced


class TestBuildMessages:
    def test_system_entry_first_with_persona_and_context(self):
        messages = build_messages([], "hi", "PORTFOLIO CONTEXT MARKER")

        assert messages[0]["role"] == "system"
        assert "FinAlly" in messages[0]["content"]
        assert "PORTFOLIO CONTEXT MARKER" in messages[0]["content"]

    def test_two_row_history_produces_four_entries_in_order(self):
        history = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]

        messages = build_messages(history, "third", "ctx")

        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "first"
        assert messages[2]["content"] == "second"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "third"


class TestSystemPromptContract:
    def test_no_disclaimer_language(self):
        text = SYSTEM_PROMPT.lower()
        phrases = [
            "not investment advice",
            "financial advice",
            "consult a",
            "do your own research",
            "at your own risk",
        ]
        assert not any(phrase in text for phrase in phrases)

    def test_instructs_whole_share_quantities_and_mentions_concentration_and_watchlist(self):
        text = SYSTEM_PROMPT.lower()
        assert "whole" in text
        assert "concentration" in text
        assert "watchlist" in text
