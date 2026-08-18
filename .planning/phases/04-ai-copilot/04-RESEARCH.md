# Phase 4: AI Copilot - Research

**Researched:** 2026-08-17
**Domain:** LLM structured-output tool-calling over an existing HTTP-agnostic service layer (FastAPI + LiteLLM/OpenRouter/Cerebras + SQLite)
**Confidence:** MEDIUM-HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Chat Panel UI & Interactions**
- D-01: The transcript renders as chat bubbles (user/assistant, left/right aligned), not a flat terminal log.
- D-02: The message input is pinned at the bottom of the chat panel, transcript scrolls above it — matches `TradeBar`'s existing fixed-input convention.
- D-03: While waiting for a response, show an animated typing-dots indicator in place of the assistant's next message bubble.
- D-04: An executed trade or watchlist change renders as a distinct bordered action card beneath the assistant's message (e.g. "✓ Bought 5 AAPL @ $190.23") — visually separated from prose so executed actions are unmistakable at a glance.

**Assistant Personality & Tone**
- D-05: Voice is terse/data-first — short sentences, leads with numbers, minimal hedging. Matches PLAN.md's "concise and data-driven" instruction and the Bloomberg-terminal aesthetic.
- D-06: Declined trades (insufficient cash, overselling) are explained directly with exact numbers — e.g. "Can't buy 50 TSLA — that's $12,450 but you have $8,200 cash." Mirrors the trade bar's existing inline-error precedent.
- D-07: The assistant is reactive only — it analyzes/trades/edits the watchlist when the user asks or explicitly agrees to a suggestion in the same turn. It does not volunteer trade ideas unprompted.
- D-08: No financial-advice disclaimer language anywhere in responses — it's a $10k simulator with zero real-world stakes.

**Trade Execution via Chat**
- D-09: LLM-initiated trades stay whole-share only this phase, consistent with the manual trade bar (Phase 2 D-03). The assistant does not compute fractional quantities from dollar-amount requests. `execute_trade()` and the `positions`/`trades` schema remain float-typed/ready for fractional trading to be enabled later without a migration.

**Message History**
- D-10: On page load, fetch the full persisted `chat_messages` history, capped at a reasonable count (e.g. last 100 messages).
- D-11: The transcript auto-scrolls to the newest message on load, matching how it will auto-scroll as new messages arrive during a live session.
- D-12: No visual divider between restored prior history and this session's new messages.

### Claude's Discretion
- Exact action-card styling (border color, icon, spacing) within the dark-terminal theme and existing panel conventions.
- Exact typing-dots animation implementation (CSS vs. a small library-free component).
- The precise history cap number ("reasonable," e.g. 100 — tune based on payload size).
- Whether failed-trade action cards get a distinct visual treatment from successful ones, or whether failures are prose-only (no action card).

### Deferred Ideas (OUT OF SCOPE)
- Fractional/dollar-amount trades via chat ("buy $500 of AAPL") — schema and `execute_trade()` stay ready for it.
- Proactive/unprompted trade suggestions — the assistant only acts when asked or agreed to in-turn.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | Send a chat message, receive complete structured JSON response (message + executed actions) | `POST /api/chat` endpoint spec below; LiteLLM structured-output call pattern; `ChatResponse` Pydantic schema |
| CHAT-02 | Assistant analyzes portfolio composition, risk concentration, and P&L when asked | Portfolio-context builder pattern (reuses `get_portfolio()` + `PriceCache`); system prompt template below |
| CHAT-03 | Assistant auto-executes trades the user agrees to, no confirmation dialog | Reuse `execute_trade()` directly; per-trade try/except loop pattern below |
| CHAT-04 | Assistant adds/removes watchlist tickers via natural language | Reuse `add_ticker()`/`remove_ticker()` directly |
| CHAT-05 | Failed LLM-initiated trades surface as a plain-language explanation, portfolio unchanged | `TradeRejected.detail()` → message-mapping pattern (mirrors `frontend/lib/trade.ts`); action items carry `status: "failed"` |
| CHAT-06 | Chat history persists across reloads (`chat_messages` table) | **Gap found**: PLAN.md §8 declares no `GET` history endpoint — see Open Questions #1. Schema and read/write pattern below. |
| CHAT-07 | Loading indicator shows while waiting for the LLM response | Frontend-only; D-03 typing-dots; no backend streaming needed (see Common Pitfalls #1) |
| CHAT-08 | LLM calls use LiteLLM → OpenRouter → Cerebras (`gpt-oss-120b`) with structured outputs, per the skill | Verified via Context7 (official LiteLLM source) — exact call pattern, `extra_body` provider routing, strict-schema conversion below |
| CHAT-09 | `LLM_MOCK=true` returns deterministic mock responses, no external call | No existing mock precedent in repo — this phase establishes the pattern fresh; recommended design below |
| TEST-02 | Backend unit tests cover structured-output parsing, including malformed responses | Recommended test architecture: separate pure `parse_response()` function, tested directly with valid/invalid JSON fixtures — no LiteLLM mocking required |
</phase_requirements>

## Summary

This phase adds a single new backend package, `app/chat/`, that follows the exact same shape as the existing `app/portfolio/` and `app/watchlist/` packages: a router factory (`create_chat_router(cache)`), an HTTP-agnostic service module, and Pydantic models. The one new external dependency is `litellm`, called synchronously per the `cerebras-inference` skill's mandated pattern (`completion(model=..., response_format=PydanticModel, extra_body={"provider": {"order": ["cerebras"]}})`) and wrapped in `run_in_threadpool` to avoid blocking the FastAPI event loop — the same discipline this codebase already applies to `execute_trade()` and `add_ticker()`.

The structured-output schema (`message`, `trades[]`, `watchlist_changes[]`) should be a plain Pydantic model with **no field-level constraints** (no `Field(pattern=...)`, no `conlist(min_items=...)`) — Cerebras's strict JSON-schema mode (verified via official docs) does not support regex patterns or array length constraints, and LiteLLM's built-in Pydantic→strict-schema conversion (verified via Context7/official LiteLLM source) already handles `additionalProperties: false` and required-field marking automatically. All real validation — ticker shape, trade legality, cash sufficiency — happens *after* parsing, by calling the exact same `execute_trade()` and `add_ticker()`/`remove_ticker()` functions the manual trade bar and watchlist form already use. The LLM never bypasses domain validation; worst case it proposes a trade that gets rejected exactly like a bad manual trade would.

One gap surfaced during research: PLAN.md §8 lists only `POST /api/chat` under the Chat endpoints table, but CONTEXT.md D-10 requires fetching full persisted history on page load (CHAT-06). No `GET` history endpoint is specified anywhere. The planner must add one — recommended name `GET /api/chat/history`, mirroring `GET /api/portfolio/history`'s existing naming convention.

**Primary recommendation:** Build `app/chat/` as a fourth sibling package to `market/`, `portfolio/`, `watchlist/`, reusing `execute_trade()`/`add_ticker()`/`remove_ticker()` directly for all state changes, wrapping the synchronous `litellm.completion()` call in `run_in_threadpool`, and adding a `GET /api/chat/history` endpoint not explicitly listed in PLAN.md but required by CHAT-06/D-10.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Chat message send/receive (HTTP) | API / Backend | Browser / Client | `POST /api/chat` does the LLM round-trip; client only renders |
| Portfolio/watchlist context assembly for the prompt | API / Backend | — | Reads `PriceCache` + SQLite directly, same as `get_portfolio()` already does |
| LLM call + structured-output parsing | API / Backend | — | LiteLLM call is synchronous and must never reach the browser; API key is server-only |
| Trade / watchlist auto-execution | API / Backend | Database / Storage | Delegates to existing `execute_trade()`/`add_ticker()`/`remove_ticker()` — no new validation logic |
| Chat history persistence | Database / Storage | API / Backend | `chat_messages` table already exists; backend owns reads/writes |
| Chat transcript, bubbles, typing indicator, action cards | Browser / Client | — | Pure rendering of data already returned by `POST /api/chat` and `GET /api/chat/history` |
| `LLM_MOCK` gate | API / Backend | — | Environment-read must happen server-side before any LiteLLM import is exercised |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| litellm | 1.97.0 (latest, verified on PyPI) | Unified client for OpenRouter/Cerebras chat completions with structured-output support | Mandated by `.claude/skills/cerebras/SKILL.md` (project-fixed, not open for revisiting); official BerriAI package |
| pydantic | 2.13.4 (already in the dependency tree via FastAPI) | Structured-output schema definition (`response_format=MyModel`) and request/response validation | Already used throughout `app/portfolio/routes.py`, `app/watchlist/routes.py`; LiteLLM natively accepts a Pydantic class as `response_format` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.2.2 (already installed — transitive via `uvicorn[standard]`, currently *unused* by app code) | Load `OPENROUTER_API_KEY` from `.env` for local `uv run uvicorn` dev | See Common Pitfalls #3 — nothing in `app/` currently calls `load_dotenv()` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LiteLLM `completion()` (sync, wrapped in `run_in_threadpool`) | LiteLLM `acompletion()` (native async) | The `cerebras-inference` skill's mandated snippet uses sync `completion()` — following it exactly is the locked constraint; `run_in_threadpool` gets the same non-blocking benefit without deviating from the skill |
| Pydantic `response_format` (LiteLLM auto-converts to strict JSON schema) | Hand-built `dict` JSON schema | LiteLLM's auto-conversion already produces `additionalProperties: false` and marks fields required correctly (verified via Context7/official source) — hand-rolling risks missing a strict-mode requirement |

**Installation:**
```bash
cd backend
uv add litellm pydantic
```

**Version verification:** `pip index versions litellm` returned `1.97.0` as latest, with an unbroken release history back to `0.1.0` (600+ releases) `[VERIFIED: pypi registry]`. `pydantic` is already resolved in `backend/uv.lock` at `2.13.4` via the existing FastAPI dependency chain and is already imported directly in `app/portfolio/routes.py`/`app/watchlist/routes.py` — adding it explicitly to `dependencies` (per the skill) makes that already-real dependency direct rather than transitive.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|-------------|
| litellm | PyPI | 3+ years (releases back to `0.1.0`, latest `1.97.0`) `[VERIFIED: pypi registry]` | Not returned by the legitimacy seam for this ecosystem (signals came back `null`) | `github.com/BerriAI/litellm` — Context7 lists it "High" source reputation with 16,110 indexed code snippets | **SUS** (automated seam) — signals were `unknown-age`/`unknown-downloads`/`no-repository`, i.e. the seam could not populate PyPI-specific signals, not that it found anything suspicious | Flagged per protocol — planner should add a `checkpoint:human-verify` task before `uv add litellm`, even though manual cross-check (PyPI release history + Context7 official-source reputation + this package being the one explicitly mandated by `.claude/skills/cerebras/SKILL.md`) found no actual red flags |
| pydantic | PyPI | Years-old, ubiquitous (already resolved in `backend/uv.lock` at 2.13.4) | N/A — already an active transitive dependency in this codebase, imported directly in existing routes | `github.com/pydantic/pydantic` | OK | Approved — already in use, no new supply-chain surface |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `litellm` — see disposition above; the SUS verdict stems from the legitimacy seam lacking PyPI-specific signal collection (age/downloads/repo came back `null`, not negative), not from any discovered red flag. `pip index versions litellm` and Context7's official-source listing both independently corroborate legitimacy.

## Architecture Patterns

### System Architecture Diagram

```
Browser (chat panel)
   |  POST /api/chat { message: string }
   v
create_chat_router(cache)              <- new, same factory shape as create_portfolio_router
   |
   v
app/chat/service.py: handle_chat_message()
   |
   |-- 1. build_context(cache)  ---------> reads PriceCache + get_portfolio() + db.watchlist_tickers()
   |-- 2. load_recent_history(limit=N) --> SELECT chat_messages ORDER BY created_at DESC LIMIT N
   |-- 3. call_llm(messages)  -----------> LLM_MOCK=true?  --yes--> deterministic mock ChatResponse
   |                                        |no
   |                                        v
   |                                 litellm.completion(model=MODEL, response_format=ChatResponse,
   |                                     extra_body=EXTRA_BODY, reasoning_effort="low")
   |                                        |  (wrapped in run_in_threadpool -- sync call)
   |                                        v
   |                                 OpenRouter -> Cerebras -> openai/gpt-oss-120b
   |
   |-- 4. parse_response(raw_json) -------> ChatResponse.model_validate_json(raw) or ParseError
   |
   |-- 5. for trade in response.trades:
   |         try: execute_trade(ticker, side, quantity, cache)  <- same function TradeBar uses
   |         except TradeRejected as e: record failed action, do not mutate state
   |
   |-- 6. for change in response.watchlist_changes:
   |         add_ticker(ticker) / remove_ticker(ticker)          <- same functions WatchlistAddForm uses
   |
   |-- 7. persist user message + assistant message + actions[] --> INSERT INTO chat_messages (x2)
   |
   v
Return { message, actions[] } as JSON  -->  Browser renders bubble + action cards,
                                              then re-fetches /api/portfolio, /api/portfolio/history,
                                              /api/watchlist (same handleTraded()/handleAdded() pattern
                                              page.tsx already uses after a manual trade)
```

### Recommended Project Structure
```
backend/app/chat/
├── __init__.py       # exports create_chat_router, service functions, exception types
├── models.py          # ChatResponse, TradeAction, WatchlistAction Pydantic models; ChatRejected? (none needed -- chat itself can't be "rejected", only individual actions within it)
├── llm.py             # call_llm() (LiteLLM wrapper) + parse_response() (pure, testable) + mock_response()
├── service.py          # handle_chat_message(): context building, history load/save, action execution loop
└── routes.py           # create_chat_router(cache): POST /api/chat, GET /api/chat/history

backend/tests/chat/
├── __init__.py
├── test_llm.py         # parse_response() with valid + malformed JSON fixtures (TEST-02) -- no LiteLLM mocking
├── test_service.py     # handle_chat_message() with a monkeypatched call_llm(), asserting trade/watchlist side effects
└── test_routes.py      # POST /api/chat and GET /api/chat/history over TestClient, LLM_MOCK=true

frontend/components/
├── ChatPanel.tsx        # replaces ChatPlaceholder in page.tsx
├── ChatMessage.tsx       # one bubble (user or assistant)
├── ChatActionCard.tsx    # D-04 bordered action card
└── ChatTypingIndicator.tsx  # D-03 typing-dots

frontend/lib/
├── chat.ts              # pure: message formatting, action-card copy mapping (mirrors trade.ts/watchlistForm.ts)
└── useChatHistory.ts     # optional: fetch-on-mount + append-on-send hook (mirrors usePriceHistory.ts's shape)
```

### Pattern 1: Router factory bound to the shared cache
**What:** `create_chat_router(cache: PriceCache) -> APIRouter`, registered in `main.py` alongside the other three routers, before the static mount.
**When to use:** Every new HTTP surface in this codebase follows this exact factory shape — it is not optional discretion, it is an established convention (see `create_stream_router`, `create_portfolio_router`, `create_watchlist_router`).
**Example:**
```python
# Source: backend/app/portfolio/routes.py:26-34 (existing pattern, read this session)
def create_portfolio_router(cache: PriceCache) -> APIRouter:
    router = APIRouter()

    @router.get("/api/portfolio")
    async def portfolio() -> dict:
        return await run_in_threadpool(get_portfolio, cache)
    ...
    return router
```
Apply identically for `create_chat_router(cache)`.

### Pattern 2: Sync external call wrapped in `run_in_threadpool`
**What:** Every synchronous, potentially-slow call in this codebase (`execute_trade`, `get_portfolio`, `add_ticker`) is invoked from an `async def` route via `await run_in_threadpool(fn, *args)`. LiteLLM's mandated `completion()` (not `acompletion()`) is synchronous and must follow the same rule — this project's own CLAUDE.md explicitly calls out "Synchronously calling [a network client] from FastAPI" as an anti-pattern to avoid.
**Example:**
```python
# Source: backend/app/portfolio/routes.py:44-48 (existing pattern, read this session)
result = await run_in_threadpool(
    execute_trade, request.ticker, request.side, request.quantity, cache
)
```
Apply the same wrapper around the LiteLLM call: `raw = await run_in_threadpool(call_llm, messages)`.

### Pattern 3: The exact LiteLLM structured-output call (mandatory, from `.claude/skills/cerebras/SKILL.md`)
**What:** The precise call shape this phase's `/api/chat` implementation MUST follow — not open for revisiting per CONTEXT.md's canonical references.
**Example:**
```python
# Source: .claude/skills/cerebras/SKILL.md (project skill, read this session, verbatim)
from litellm import completion

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

response = completion(
    model=MODEL,
    messages=messages,
    response_format=ChatResponse,       # a pydantic.BaseModel subclass
    reasoning_effort="low",
    extra_body=EXTRA_BODY,
)
result = response.choices[0].message.content
result_as_object = ChatResponse.model_validate_json(result)
```
`messages` is a standard OpenAI-style list of `{"role": ..., "content": ...}` dicts: one `"system"` entry (persona + portfolio/watchlist context + instructions), then the recent conversation history, then the new user message.

### Pattern 4: Structured-output schema shaped for Cerebras strict mode
**What:** Cerebras's strict JSON-schema mode (official docs, fetched this session) requires every object to set `additionalProperties: false` and effectively marks all fields required; it does **not** support regex `pattern`, string `format` (email/date-time/uuid), or array `minItems`/`maxItems`. LiteLLM's Pydantic→schema conversion (verified via Context7, official LiteLLM source `llms/base_llm/base_utils.py`) already emits `additionalProperties: false` and `strict: true` automatically for a plain `BaseModel` — so the schema must avoid `Field(pattern=...)`, `conlist`, or any other constraint LiteLLM would otherwise pass through into the schema.
**Example:**
```python
# app/chat/models.py -- illustrative, not copied from any source
from pydantic import BaseModel


class TradeAction(BaseModel):
    ticker: str
    side: str          # "buy" | "sell" -- validate against the literal set in Python, not a schema enum/pattern
    quantity: int       # whole shares only per D-09; "type": "integer" is a supported strict-mode constraint


class WatchlistAction(BaseModel):
    ticker: str
    action: str          # "add" | "remove"


class ChatResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistAction] = []
```
Note: do **not** use `Literal["buy", "sell"]` type hints if avoidable friction with strict-mode enum limits is a concern (Cerebras docs list enums as supported up to 500 values total, so `Literal` is fine here — flagging only as something to confirm empirically once real calls are made, since the model, not just the schema, must reliably emit one of the two values; see Common Pitfalls #2).

### Anti-Patterns to Avoid
- **Re-implementing trade/watchlist validation inside the chat handler:** `execute_trade()` and `add_ticker()`/`remove_ticker()` already own every validation rule (cash sufficiency, share ownership, ticker shape, watchlist cap). The chat handler's only job is to call them and translate the resulting `TradeRejected`/`WatchlistRejected` exception into a message-friendly explanation — exactly like `frontend/lib/trade.ts`'s `tradeErrorMessage()` already does for the manual trade bar, just server-side this time (D-06's exact-numbers requirement comes straight out of `TradeRejected.detail()`'s existing payload shape: `cost`, `cash_balance`, `owned`).
- **Hand-building the JSON schema dict:** let LiteLLM's Pydantic conversion do it; a hand-rolled schema risks missing `additionalProperties: false` or a required-field marker that strict mode demands.
- **Calling `litellm.completion()` directly on the event loop:** blocks all other requests (including the SSE price stream) for the duration of the LLM round-trip.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| LLM API client, provider routing, retries | A custom `httpx` wrapper around OpenRouter's REST API | `litellm.completion()` per the mandated skill | Already handles OpenRouter auth headers, response parsing, and Cerebras provider-order routing via `extra_body` |
| JSON-schema generation from the response model | A hand-written `dict` schema | `response_format=ChatResponse` (a `BaseModel` subclass) | LiteLLM's `type_to_response_format_param()` auto-produces a strict-mode-correct schema (verified via Context7) |
| Trade legality checks (cash, shares, ticker liveness) | New validation logic inside the chat handler | `execute_trade()` (`backend/app/portfolio/service.py`) | Already covers every edge case (insufficient cash, oversell, untradable ticker) with tested exception types |
| Watchlist ticker shape/dup/cap checks | New regex + count logic in the chat handler | `add_ticker()`/`remove_ticker()` (`backend/app/watchlist/service.py`) | Already normalizes, validates `^[A-Z]{1,10}$`, and enforces the 50-ticker cap |
| Structured-output validation | Manual `json.loads()` + `if "message" not in data: ...` key checks | `ChatResponse.model_validate_json(raw)` inside a `try/except ValidationError` | Pydantic already produces precise field-level errors for TEST-02's malformed-response tests |

**Key insight:** every piece of *domain logic* this phase needs (trade execution, watchlist mutation, portfolio valuation) already exists as an HTTP-agnostic function from Phases 1-3. This phase is almost entirely glue: build a prompt, parse a structured response, and call functions that already exist. The only genuinely new logic is prompt construction, response parsing/error handling, and chat history read/write — everything else is reuse.

## Common Pitfalls

### Pitfall 1: Treating the LLM call like it needs streaming infrastructure
**What goes wrong:** Building SSE or chunked-response plumbing for the chat endpoint when PLAN.md explicitly says none is needed ("Cerebras inference is fast enough that a loading indicator is sufficient").
**Why it happens:** The rest of the app (prices) streams via SSE, so it's tempting to reuse that pattern reflexively.
**How to avoid:** `POST /api/chat` returns one complete JSON body (CHAT-01). The loading indicator (CHAT-07, D-03) is purely a frontend `submitting` boolean state — same shape as `TradeBar.tsx`'s existing `submitting` flag — held while the `fetch()` promise is in flight.
**Warning signs:** Any code touching `EventSourceResponse` or `sse_starlette` inside `app/chat/`.

### Pitfall 2: gpt-oss-120b structured-output reliability under different inference backends
**What goes wrong:** `[CITED: community.groq.com]` and `[CITED: github.com/lmstudio-ai]` reports describe `response_format`/strict JSON schema being ignored or producing free-form text for `gpt-oss-120b` on *some* inference backends (Groq, LM Studio) — the model can emit reasoning/commentary text alongside or instead of the schema-conforming JSON in edge cases. This has **not** been confirmed specifically against Cerebras's own inference stack (Cerebras's own docs, `[CITED: inference-docs.cerebras.ai/capabilities/structured-outputs]`, describe `gpt-oss-120b` as their documented structured-output example model and state strict mode "guarantees" schema-matching output) — but the model family's known behavior under load argues for defensive parsing regardless of provider claims.
**Why it happens:** `gpt-oss`'s "Harmony" response format includes reasoning traces that can interleave with or crowd out the structured payload in some serving stacks.
**How to avoid:** Always wrap `ChatResponse.model_validate_json(result)` in `try/except (ValidationError, json.JSONDecodeError)`. On failure, do not crash the request — return a fallback `ChatResponse(message="Something went wrong processing that — try rephrasing.", trades=[], watchlist_changes=[])` (or a 502 if the planner prefers explicit failure surfacing) and log the raw response for debugging. This is exactly what TEST-02 asks unit tests to cover.
**Warning signs:** `model_validate_json` raising in local manual testing even though the schema and prompt look correct — check `response.choices[0].message.content` for leaked reasoning text or truncation before assuming the schema itself is wrong.

### Pitfall 3: `OPENROUTER_API_KEY` never actually loaded from `.env`
**What goes wrong:** `os.getenv("OPENROUTER_API_KEY")` returns `None` when running `uv run uvicorn app.main:app` locally, because **nothing in `app/` currently calls `load_dotenv()`** `[VERIFIED: backend/app/main.py — no dotenv import; backend/app/market/factory.py:12 reads os.getenv("MASSIVE_API_KEY", "") with no prior dotenv load anywhere in the codebase]`. `python-dotenv` is installed in the venv only as `uvicorn[standard]`'s optional extra (for uvicorn's own `--env-file` CLI flag), not invoked by app code.
**Why it happens:** Phases 1-3 never needed a secret key (`MASSIVE_API_KEY` is optional and the simulator needs no key), so this gap was never exercised.
**How to avoid:** Either (a) add an explicit `from dotenv import load_dotenv; load_dotenv()` near the top of `app/main.py` (or `app/chat/llm.py`) so local `uv run` picks up the root `.env`, or (b) document that the app must always be started with `uvicorn --env-file ../.env` / Docker `--env-file`. Given Docker (`docker run --env-file .env`, per PLAN.md §11) already covers the production path, the gap only bites local `uv run` dev/test — but it will silently break local manual verification of this phase unless addressed. `python-dotenv` is already an explicit CLAUDE.md-listed dependency; adding the one `load_dotenv()` call is the cheapest fix.
**Warning signs:** LiteLLM/OpenRouter calls failing with 401 locally despite the key being present in `.env`.

### Pitfall 4: Silent partial failure across multiple LLM-proposed actions
**What goes wrong:** The LLM proposes two trades in one turn; the first succeeds and mutates cash, the second fails with `InsufficientCashError` because the first trade already spent the cash. If the handler doesn't process actions sequentially and re-derive state between them, or doesn't clearly report per-action outcomes, the user sees an ambiguous response.
**Why it happens:** `execute_trade()` reads the *current* cash balance fresh on every call (it's not handed a stale snapshot), so sequential execution is naturally correct — but only if the handler loops one action at a time and captures each outcome rather than batching.
**How to avoid:** Iterate `response.trades` and `response.watchlist_changes` one at a time, wrapping each in its own `try/except`, appending a `{"status": "executed", ...}` or `{"status": "failed", "code": ..., ...}` entry to the `actions` list per action — never abort the whole batch on the first failure (D-05/D-06 imply the assistant should still report what *did* work).
**Warning signs:** A test where the LLM mock proposes two trades and only one cash-balance delta appears in the final state, with no failure detail for the other.

### Pitfall 5: History cap must be read newest-first then reversed for display order
**What goes wrong:** `SELECT ... ORDER BY created_at LIMIT 100` on a long history returns the *oldest* 100 messages, not the most recent 100 (D-10 wants the most recent messages, capped).
**Why it happens:** Easy to copy `get_portfolio_history()`'s `LIMIT` pattern without noticing it also does `ORDER BY ... DESC ... LIMIT` then reverses in Python.
**How to avoid:** Mirror `get_portfolio_history()` exactly (`backend/app/portfolio/service.py:140-159`, read this session): `ORDER BY created_at DESC, rowid DESC LIMIT ?` then `reversed(rows)` in Python before returning, so the API always returns chronological order but the cap keeps the *newest* N.
**Warning signs:** A fresh conversation with >100 messages showing only the earliest exchanges after reload.

## Code Examples

### Reading recent chat history (mirrors `get_portfolio_history`)
```python
# Pattern source: backend/app/portfolio/service.py:140-159 (read this session, adapted)
def get_recent_messages(limit: int = 100) -> list[dict]:
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT role, content, actions, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (DEFAULT_USER_ID, limit),
        ).fetchall()
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "actions": json.loads(row["actions"]) if row["actions"] else None,
            "created_at": row["created_at"],
        }
        for row in reversed(rows)
    ]
```

### Persisting a message (mirrors the `?`-placeholder convention used everywhere else)
```python
# Pattern source: backend/app/portfolio/service.py:280-292 _insert_trade() (read this session, adapted)
def _insert_chat_message(
    conn: sqlite3.Connection, role: str, content: str, actions: list[dict] | None
) -> None:
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            uuid.uuid4().hex,
            DEFAULT_USER_ID,
            role,
            content,
            json.dumps(actions) if actions is not None else None,
            datetime.now(UTC).isoformat(),
        ),
    )
```

### `LLM_MOCK` gate (no existing precedent — recommended fresh pattern)
```python
# app/chat/llm.py -- illustrative, no existing repo precedent to cite
import os

def call_llm(messages: list[dict]) -> str:
    if os.getenv("LLM_MOCK", "").lower() == "true":
        return _mock_response(messages).model_dump_json()
    response = completion(
        model=MODEL, messages=messages, response_format=ChatResponse,
        reasoning_effort="low", extra_body=EXTRA_BODY,
    )
    return response.choices[0].message.content


def _mock_response(messages: list[dict]) -> ChatResponse:
    """Deterministic: same shape every call, no external request. Exact
    canned content is Claude's discretion at plan/implementation time --
    only the determinism and zero-network-call properties are required
    by CHAT-09."""
    return ChatResponse(message="Mock response.", trades=[], watchlist_changes=[])
```

## Runtime State Inventory

Not applicable — this is a greenfield phase (new package, new endpoints), not a rename/refactor/migration. `chat_messages` is an existing table created by `initialize()` since Phase 1 but has never been written to; there is no pre-existing runtime state to migrate.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | The `actions` JSON column's exact shape (`[{"type": "trade", "status": "executed"/"failed", ...}, {"type": "watchlist_add"/"watchlist_remove", ...}]`) — no prior spec beyond PLAN.md's "JSON — trades executed, watchlist changes made" | Code Examples, Architecture Patterns | Low — this is purely an internal contract between `service.py` and the frontend's action-card renderer; the planner/executor can freely shape it as long as both sides agree |
| A2 | `LLM_MOCK` mock response design (fixed canned `ChatResponse`, ignoring message content) | Code Examples | Low-Medium — if E2E tests (Phase 5, TEST-04) need the mock to react to specific phrases (e.g. "buy 5 AAPL" actually triggering a mock trade), a smarter mock keyed on message content may be needed instead of a single fixed reply |
| A3 | `GET /api/chat/history` as the recommended new endpoint name/path (not in PLAN.md §8) | Phase Requirements, Open Questions #1 | Low — any reasonable name works as long as it's documented; naming consistency with `/api/portfolio/history` is a style choice, not a hard requirement |
| A4 | Cerebras's own inference stack has not been directly confirmed (only Groq/LM Studio reports found) to reproduce gpt-oss-120b's occasional structured-output-ignored behavior — Cerebras's own docs claim strict-mode guarantees | Common Pitfalls #2 | Medium — if this behavior *does* occur on Cerebras+OpenRouter in practice, defensive parsing (already recommended) fully covers it; if it never occurs, the defensive code is just unused-but-harmless robustness |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **No `GET` chat-history endpoint declared in PLAN.md §8, but CHAT-06/D-10 require one**
   - What we know: PLAN.md's Chat endpoints table lists only `POST /api/chat`. CONTEXT.md D-10 explicitly requires fetching full persisted history on page load, capped at ~100 messages.
   - What's unclear: The exact path/name the planner should use, since it's not in the canonical spec.
   - Recommendation: Add `GET /api/chat/history` (mirrors `GET /api/portfolio/history`'s existing naming convention) returning `list[dict]` in chronological order, capped per D-10. This is a small, low-risk addition to PLAN.md's contract that the planner should make explicit in the phase plan.

2. **Whether `TradeAction.side`/`WatchlistAction.action` should be `Literal[...]` or plain `str` in the structured-output schema**
   - What we know: Cerebras strict mode supports enums (up to 500 values, per official docs), so `Literal["buy", "sell"]` should produce a valid, LiteLLM-generated enum constraint.
   - What's unclear: Whether constraining via `Literal` in the schema measurably improves the model's reliability at emitting exactly `"buy"`/`"sell"` versus validating the returned string in Python after the fact (matching `execute_trade()`'s own `if side not in ("buy", "sell")` check, which already exists and fires regardless).
   - Recommendation: Use `Literal["buy", "sell"]` in the schema for defense-in-depth (letting strict mode do some of the work), but keep `execute_trade()`'s own validation as the actual enforcement boundary — this costs nothing extra since that check already exists.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `OPENROUTER_API_KEY` env var | Every real (non-`LLM_MOCK`) chat call | Present in root `.env` per CLAUDE.md, but **not currently loaded into the process environment by any app code** (see Common Pitfalls #3) | — | `load_dotenv()` call, or start with `--env-file` |
| Network access to `openrouter.ai` | Real LLM calls | Assumed available (sandboxed dev environment allowlists `openrouter.ai`? not directly confirmed — CLAUDE tool sandbox network allowlist in this session lists `massive.com`, `pypi.org`, `polygon.io`, `github.com`, `files.pythonhosted.org`, `registry.npmjs.org`, **not** `openrouter.ai`) | — | `LLM_MOCK=true` for any sandboxed automated verification; real key testing needs a non-sandboxed run |
| `litellm` package | All LLM calls | Not yet installed — `uv add litellm pydantic` | 1.97.0 latest | None — required |

**Missing dependencies with no fallback:**
- None — `LLM_MOCK=true` is itself the documented fallback path for CI/sandboxed/E2E environments per CHAT-09.

**Missing dependencies with fallback:**
- `OPENROUTER_API_KEY` loading — fallback is adding one `load_dotenv()` call (see Pitfall 3).
- Network access to `openrouter.ai` from within this coding-agent sandbox — fallback is `LLM_MOCK=true` for any automated verification run inside this session; real-key verification should happen outside the sandbox or with an explicit sandbox override.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (≥8.3.0 per `backend/pyproject.toml`, 9.1.1 installed per CLAUDE.md) + pytest-asyncio (`asyncio_mode = "auto"`) |
| Backend config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Backend quick run | `cd backend && uv run --extra dev pytest tests/chat -x` — **must use `--extra dev`**; plain `uv run pytest` silently falls through to a system pytest lacking `pytest-asyncio` (known project gotcha, confirmed in prior session memory) |
| Backend full suite | `cd backend && uv run --extra dev pytest` |
| Frontend framework | Vitest ^4.1.10 |
| Frontend config | `frontend/vitest.config.ts` (not read this session, but `npm test` → `vitest run` per `package.json`) |
| Frontend quick run | `cd frontend && npm test -- lib/chat` (once `lib/chat.test.ts` exists) |
| Frontend full suite | `cd frontend && npm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|--------------|
| CHAT-01 | `POST /api/chat` returns `{message, actions}` shaped JSON | integration | `uv run --extra dev pytest tests/chat/test_routes.py -x` | ❌ Wave 0 |
| CHAT-02 | Portfolio context (positions, cash, concentration, P&L) reaches the LLM prompt | unit | `uv run --extra dev pytest tests/chat/test_service.py::test_build_portfolio_context -x` | ❌ Wave 0 |
| CHAT-03 | A trade proposed + agreed executes via `execute_trade()`, no confirmation | unit (mocked `call_llm`) | `uv run --extra dev pytest tests/chat/test_service.py -k trade -x` | ❌ Wave 0 |
| CHAT-04 | Watchlist add/remove executes via `add_ticker`/`remove_ticker` | unit (mocked `call_llm`) | `uv run --extra dev pytest tests/chat/test_service.py -k watchlist -x` | ❌ Wave 0 |
| CHAT-05 | Insufficient-cash/oversell trade surfaces as explanation, portfolio unchanged | unit | `uv run --extra dev pytest tests/chat/test_service.py -k rejected -x` | ❌ Wave 0 |
| CHAT-06 | History persists and is readable after "reload" (fresh `GET`) | integration | `uv run --extra dev pytest tests/chat/test_routes.py -k history -x` | ❌ Wave 0 |
| CHAT-07 | Loading indicator — frontend-only, no backend test | manual/frontend | `cd frontend && npm test -- ChatPanel` | ❌ Wave 0 (frontend) |
| CHAT-08 | Call shape matches skill exactly (model, `extra_body`, `response_format`) | unit (assert call args on a monkeypatched `litellm.completion`) | `uv run --extra dev pytest tests/chat/test_llm.py -k call_shape -x` | ❌ Wave 0 |
| CHAT-09 | `LLM_MOCK=true` → deterministic response, zero network calls | unit | `uv run --extra dev pytest tests/chat/test_llm.py -k mock -x` | ❌ Wave 0 |
| TEST-02 | `parse_response()` handles valid and malformed JSON | unit | `uv run --extra dev pytest tests/chat/test_llm.py -k parse -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** targeted `tests/chat/` file for the module just touched
- **Per wave merge:** `uv run --extra dev pytest` (backend) + `npm test` (frontend)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/chat/__init__.py`, `test_llm.py`, `test_service.py`, `test_routes.py` — new test package, no existing coverage
- [ ] `frontend/lib/chat.test.ts`, `frontend/components/*.test.tsx` for the new chat components — mirrors existing `lib/trade.test.ts`/`lib/watchlistForm.test.ts` shape
- [ ] No new test framework install needed — pytest-asyncio and Vitest are already configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | No | App remains zero-auth, single hardcoded `user_id="default"` per project constraints |
| V3 Session Management | No | No sessions introduced |
| V4 Access Control | No | Single-user; no new access boundaries |
| V5 Input Validation | Yes | Pydantic validates the `POST /api/chat` request body (`{message: str}`); LLM-proposed tickers/quantities are **never** trusted directly — they pass through `normalize_ticker()`/`execute_trade()`'s existing validation before any write, exactly like manually-entered input |
| V6 Cryptography | No new surface | `OPENROUTER_API_KEY` is a bearer secret, not cryptographic material generated by this app; standard secret-handling applies (never logged, never echoed to the client) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Prompt injection via user chat message (user tries to manipulate the assistant into disclosing the system prompt, or into proposing an action the user themselves couldn't have made) | Tampering / Information Disclosure | Low real-world impact here: every action the LLM proposes still passes through `execute_trade()`/`add_ticker()`'s full validation — the LLM has no privilege beyond what the user already has via the manual trade bar/watchlist form on this single-user, zero-real-money simulator. System prompt should avoid embedding any secret beyond portfolio data the user already owns. |
| `OPENROUTER_API_KEY` leakage to the browser or logs | Information Disclosure | Read via `os.getenv()` server-side only inside `app/chat/llm.py`; never include it in the JSON response body or log statements. Consistent with the accepted-risk note already carried forward from Phase 1 (`T-01-09`: "frontend holds no secrets, revisit at Phase 4 chat panel" — this phase is that revisit; the answer is the key stays server-only, same as `MASSIVE_API_KEY` today) |
| SQL injection into `chat_messages` | Tampering | `?`-placeholder SQL exclusively, matching every other table write in this codebase — no string interpolation |
| Oversized/malformed chat message body causing wasted LLM spend or slow requests | Denial of Service | Not a hard requirement this phase; consider a reasonable message-length cap (e.g. a few thousand characters) as a light mitigation, consistent with the project's existing acceptance of "no rate limit on trade submissions" as an accepted risk (`02-SECURITY.md` T-02-10) to revisit only if Phase 5 exposes the app beyond localhost |

## Sources

### Primary (MEDIUM-HIGH confidence — Context7/official docs, read this session)
- Context7 `/berriai/litellm` — `type_to_response_format_param()` (Pydantic→strict JSON schema conversion, `additionalProperties: false` + `strict: true`), OpenRouter `extra_body`/provider-routing transformation (`llms/openrouter/chat/transformation.py`)
- `inference-docs.cerebras.ai/capabilities/structured-outputs` (WebFetch, official Cerebras docs) — strict-mode requirements, supported/unsupported schema constructs, `gpt-oss-120b` as the documented example model
- `inference-docs.cerebras.ai/integrations/openrouter` (WebFetch, official Cerebras docs) — confirms `gpt-oss-120b` structured-output support via OpenRouter
- `.claude/skills/cerebras/SKILL.md` (project-mandated, read this session) — the exact call pattern, not open for revisiting
- `pip index versions litellm` — direct PyPI registry query, confirms `1.97.0` latest with an unbroken multi-year release history

### Secondary (MEDIUM confidence — cross-checked with an official source)
- `community.groq.com` thread on `gpt-oss-120b` structured-output reliability on Groq's inference stack — not Cerebras-specific, used only to justify defensive parsing (Common Pitfalls #2), not as a claim about Cerebras itself

### Tertiary (LOW confidence — noted for validation, not treated as fact)
- `github.com/lmstudio-ai/lmstudio-bug-tracker` issue #1105 — local-inference (LM Studio) structured-output bug report for the `gpt-oss` model family; included only as corroborating context for why defensive parsing is worth the small extra code, not as evidence of a Cerebras-specific defect

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — litellm/pydantic call pattern is mandated verbatim by the project's own skill file and cross-verified against official LiteLLM source via Context7
- Architecture: HIGH — every pattern (router factory, `run_in_threadpool`, service-layer reuse) is copied directly from three already-shipped sibling packages in this exact codebase
- Pitfalls: MEDIUM — the `.env`-loading gap and history-ordering gotcha are directly verified against this repo's code; the gpt-oss-120b structured-output reliability concern is corroborated for other inference backends but not confirmed specifically on Cerebras

**Research date:** 2026-08-17
**Valid until:** 30 days (LiteLLM releases frequently; re-verify `litellm` version and Cerebras structured-output docs if planning is delayed past ~2026-09-16)
