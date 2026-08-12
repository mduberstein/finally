# LLM Mock Contract

What `LLM_MOCK=true` returns, for the E2E suite to assert against. No network,
no API key, same input always gives the same output.

Owned by `llm-engineer`. These strings are **frozen** — Playwright specs bind to
them. Changing one requires messaging `integration-tester` first.

Companion documents: `API_CONTRACT.md` (the JSON shapes),
`FRONTEND_CONTRACT.md` (test ids), `TEAM.md` (ownership and waves).

## Assistant replies

| Message sent to `POST /api/chat` | `message` in the response |
|---|---|
| `buy 10 shares of AAPL` | `Mock mode: buying 10 AAPL at the market price.` |
| `sell 4 TSLA` | `Mock mode: selling 4 TSLA at the market price.` |
| `buy NVDA` (no quantity) | `Mock mode: buying 1 NVDA at the market price.` |
| `add PYPL to the watchlist` | `Mock mode: adding PYPL to the watchlist.` |
| `remove NFLX from the watchlist` | `Mock mode: removing NFLX from the watchlist.` |
| anything else, e.g. `how is my portfolio doing?` | `Mock mode: no trade or watchlist change requested.` |

Quantity defaults to 1 and may be fractional. Tickers are case-insensitive and
upper-cased.

## Use the symbol, not the company name

`buy 10 shares of Apple` — the example phrasing in `API_CONTRACT.md` — matches
`Apple` as a five-letter symbol in mock mode and produces a **failed** trade in
a nonexistent ticker `APPLE`. Write `buy 10 shares of AAPL`.

The real LLM resolves company names correctly; only the mock's parser is
literal. This trap costs an hour if you hit it without knowing.

## Action entries are real, not mocked

The mock only decides what the assistant *asks for*. Execution runs through the
same portfolio service as a manual trade, so the `actions` entries are genuine
results.

- Executed trade:
  `{"type": "trade", "status": "executed", "detail": "Bought 10 AAPL @ $195.00", "ticker": "AAPL"}`.
  A sell reads `Sold 2.5 MSFT @ $420.00`.
- **Never assert the exact price.** The simulator moves it every 500ms. Match a
  prefix, e.g. `/^Bought 10 AAPL @ \$/`.
- Rejected trade: `status` is `"failed"`, `detail` comes verbatim from the trade
  service, and the response is still **200** — never a 4xx.
- Watchlist details: `Added PYPL to the watchlist`,
  `Removed NFLX from the watchlist`, `PYPL is already on the watchlist`,
  `PYPL is not on the watchlist`.

For an "executes a trade" scenario, `buy 2 shares of AAPL` against a fresh
$10,000 portfolio has no chance of an insufficient-cash flake.

## Endpoint behaviour

`GET /api/chat/history?limit=` defaults to 50, ascending order, `actions` is
`[]` for user messages. An empty message body is `422`. A provider failure is
`503` with `detail` — unreachable in mock mode.

## Known risk: no real provider call has ever been made

Every test stubs LiteLLM. There is no `.env` at the project root, no
`OPENROUTER_API_KEY` in the environment, and the build sandbox does not allow
`openrouter.ai`, so the live path is unexercised.

The call follows the `cerebras` skill exactly:

```python
completion(
    model="openrouter/openai/gpt-oss-120b",
    response_format=AssistantReply,
    reasoning_effort="low",
    extra_body={"provider": {"order": ["cerebras"]}},
)
```

The strict JSON schema LiteLLM generates from the Pydantic model was verified
offline to contain no keywords that strict structured outputs reject — no
`exclusiveMinimum`, `minimum`, or `pattern`. That is why
`TradeInstruction.quantity` uses a validator rather than `Field(gt=0)`.

**The first run with a real key in hand is the remaining risk.** It needs a
human with a working `OPENROUTER_API_KEY`; it cannot be closed by the E2E suite,
which runs in mock mode by design.
