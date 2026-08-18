import pytest

from app.chat.llm import EXTRA_BODY, MODEL, call_llm, mock_response, parse_response
from app.chat.models import PARSE_FALLBACK_MESSAGE, ChatResponse


class TestCallLlmMock:
    def test_mock_mode_returns_identical_reply_for_identical_input(self, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        messages = [{"role": "user", "content": "hi"}]

        first = call_llm(messages)
        second = call_llm(messages)

        assert first == second

    def test_mock_mode_never_calls_completion(self, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")

        def _boom(*args, **kwargs):
            raise AssertionError("completion should never be called in mock mode")

        monkeypatch.setattr("app.chat.llm.completion", _boom)

        call_llm([{"role": "user", "content": "hi"}])


class TestCallLlmLive:
    def test_live_call_uses_mandated_call_shape(self, monkeypatch):
        monkeypatch.delenv("LLM_MOCK", raising=False)
        recorded = {}

        class _Message:
            content = ChatResponse(message="ok").model_dump_json()

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]

        def _recorder(**kwargs):
            recorded.update(kwargs)
            return _Response()

        monkeypatch.setattr("app.chat.llm.completion", _recorder)

        call_llm([{"role": "user", "content": "hi"}])

        assert recorded["model"] == MODEL
        assert recorded["response_format"] is ChatResponse
        assert recorded["reasoning_effort"] == "low"
        assert recorded["extra_body"] == EXTRA_BODY


class TestParseResponse:
    def test_well_formed_json_parses_to_the_model(self):
        raw = ChatResponse(message="hello there").model_dump_json()

        parsed = parse_response(raw)

        assert parsed.message == "hello there"

    @pytest.mark.parametrize(
        "raw",
        [
            "not json at all",
            '{"trades": [], "watchlist_changes": []}',
            '{"message": 42}',
            'Let me think... {"message": "actually here"}',
        ],
    )
    def test_malformed_response_returns_fallback_message(self, raw):
        parsed = parse_response(raw)

        assert parsed.message == PARSE_FALLBACK_MESSAGE


class TestMockResponseActions:
    def test_buy_instruction_produces_a_trade_action(self):
        response = mock_response([{"role": "user", "content": "buy 3 AAPL"}])

        assert len(response.trades) == 1
        assert response.trades[0].ticker == "AAPL"
        assert response.trades[0].side == "buy"
        assert response.trades[0].quantity == 3
        assert response.watchlist_changes == []

    def test_sell_instruction_with_shares_of_phrasing_produces_a_trade_action(self):
        response = mock_response([{"role": "user", "content": "sell 2 shares of TSLA"}])

        assert len(response.trades) == 1
        assert response.trades[0].ticker == "TSLA"
        assert response.trades[0].side == "sell"
        assert response.trades[0].quantity == 2

    def test_watchlist_add_instruction_produces_a_watchlist_action(self):
        response = mock_response([{"role": "user", "content": "Add PYPL to my watchlist"}])

        assert response.trades == []
        assert len(response.watchlist_changes) == 1
        assert response.watchlist_changes[0].ticker == "PYPL"
        assert response.watchlist_changes[0].action == "add"

    def test_watchlist_remove_instruction_produces_a_watchlist_action(self):
        response = mock_response([{"role": "user", "content": "Remove PYPL from my watchlist"}])

        assert len(response.watchlist_changes) == 1
        assert response.watchlist_changes[0].ticker == "PYPL"
        assert response.watchlist_changes[0].action == "remove"

    def test_unmatched_message_produces_canned_reply_with_empty_arrays(self):
        response = mock_response([{"role": "user", "content": "how am I doing"}])

        assert response.trades == []
        assert response.watchlist_changes == []

    def test_repeated_calls_with_same_input_are_byte_identical(self):
        messages = [{"role": "user", "content": "buy 5 NVDA"}]

        first = mock_response(messages)
        second = mock_response(messages)

        assert first.model_dump_json() == second.model_dump_json()
