# FinAlly — AI Trading Workstation

## What This Is

FinAlly is a Bloomberg-terminal-style AI trading workstation: a single-container web app that streams live simulated market data, lets a user trade a virtual $10,000 portfolio, and includes an AI chat copilot (via OpenRouter/Cerebras) that can analyze the portfolio and execute trades on the user's behalf. It's the capstone project for an agentic AI coding course, built end-to-end by coding agents.

## Core Value

A user can watch live prices stream, trade a simulated portfolio, and have an AI assistant execute trades and manage the watchlist through natural language — all in one fluid, visually polished terminal-style interface.

## Requirements

### Validated

- ✓ Market data abstraction layer (simulator + Massive REST client behind a shared interface) — existing
- ✓ In-memory price cache with change/direction computation — existing
- ✓ Resilient background polling feed (transient-error tolerance, auth fallback, rate-limit backoff) — existing
- ✓ SSE stream router factory for `/api/stream/prices` (built but not yet wired into a running app) — existing
- ✓ FastAPI app assembly: lifespan wiring of `MarketFeed` + `PriceCache` into a running app — Phase 1 (MARKET-04)
- ✓ SQLite schema + lazy init/seed (users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages) — Phase 1 (INFRA-01)
- ✓ Watchlist read path: 10 default tickers with live SSE prices in a dark terminal grid — Phase 1 (MARKET-01, WATCH-01)
- ✓ Price flash animations (green/red, fade ~500ms) driven by the SSE stream — Phase 1 (MARKET-02)
- ✓ Connection status indicator (green/yellow/red, with staleness-aware recovery) — Phase 1 (MARKET-03)
- ✓ Dark terminal visual theme (colors per PLAN.md) built with Tailwind CSS — Phase 1 (UI-01)
- ✓ Portfolio API: `GET /api/portfolio`, `POST /api/portfolio/trade` (server-authoritative price, HTTP-agnostic `execute_trade` for future Phase 4 reuse) — Phase 2 (PORT-01..05)
- ✓ Trade execution logic: market orders, instant fill, whole-share cash/position validation, `BEGIN IMMEDIATE`-serialized concurrency — Phase 2 (PORT-02..05)
- ✓ Positions table with live price/P&L/% change overlay — Phase 2 (PORT-06, PORT-07)
- ✓ Trade bar with inline (never toast/modal) error copy — Phase 2 (UI-03)
- ✓ Append-only trade history — Phase 2 (PORT-10)
- ✓ Backend unit tests: trade execution, P&L math, concurrency, edge cases — Phase 2 (TEST-01)

### Active

- [ ] `GET /api/portfolio/history` + portfolio snapshot background task (every 30s + immediately after each trade) — deferred to Phase 3 (PORT-09)
- [ ] Watchlist write API: `POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`
- [ ] LLM chat integration: `POST /api/chat` via LiteLLM → OpenRouter (Cerebras, `gpt-oss-120b`), structured output schema, auto-executed trades/watchlist changes
- [ ] `LLM_MOCK` deterministic mode for testing
- [ ] Remaining frontend surfaces — sparkline mini-charts, main chart, portfolio heatmap, P&L chart, AI chat panel (watchlist grid, header, trade bar, positions table shipped in Phases 1-2)
- [ ] Multi-stage Dockerfile (Node build → Python runtime) serving static frontend + API on port 8000
- [ ] `docker-compose.yml` convenience wrapper
- [ ] Start/stop scripts (mac + windows)
- [ ] Backend unit tests: LLM structured-output parsing (portfolio/trade tests shipped Phase 2)
- [ ] Frontend unit tests: component rendering, watchlist CRUD, chat rendering
- [ ] Playwright E2E suite in `test/` with `docker-compose.test.yml`, `LLM_MOCK=true` scenarios

### Out of Scope

- Real Massive/Polygon market data — no Massive API key available; simulator-only for this build. The Massive client stays in the codebase as an alternate implementation but isn't exercised in production for now
- Cloud deployment (Terraform/App Runner) — Docker-only for this build; the `deploy/` stretch goal from PLAN.md is deferred
- Multi-user auth/login — explicitly zero-auth, single hardcoded `user_id="default"` per PLAN.md
- Limit orders / order book — market orders only, per PLAN.md's simplicity rationale
- Trade confirmation dialogs — instant-fill by design, including LLM-initiated trades

## Context

- This is a capstone project for an agentic AI coding course; the whole app is meant to be built by coding agents to demonstrate orchestration.
- Backend is a `uv`-managed Python 3.12+ project (`backend/pyproject.toml`, `backend/uv.lock`). FastAPI 0.141.1, sse-starlette, httpx, pydantic 2.13.4 already in use.
- The market data layer is done and tested (`backend/app/market/*`, `backend/tests/market/*`) — see `.planning/codebase/ARCHITECTURE.md` and `planning/MARKET_DATA_SUMMARY.md` for full detail. Downstream code must always read prices via `PriceCache`, never call a source's `fetch()` directly (documented anti-pattern in the codebase map).
- No `frontend/` directory exists yet — this build creates it from scratch as a Next.js static export.
- No FastAPI app entrypoint, database, or `/api/*` routes exist yet beyond the market data package.
- `.env` at project root already contains a working `OPENROUTER_API_KEY` per user confirmation.
- LLM integration must use the `cerebras-inference` skill: LiteLLM → OpenRouter → `openrouter/openai/gpt-oss-120b` on Cerebras inference, with structured outputs.

## Constraints

- **Tech stack**: Next.js (static export) + FastAPI (Python/uv) + SQLite, single Docker container on port 8000 — fixed by PLAN.md, not open for revisiting
- **Market data source**: Simulator only for this build — no Massive API key available
- **Auth**: None — single hardcoded `user_id="default"` throughout
- **Order types**: Market orders only, instant fill, no fees, no confirmation dialogs
- **LLM provider**: OpenRouter via LiteLLM, Cerebras inference, `gpt-oss-120b`, structured outputs — fixed by PLAN.md
- **Deployment**: Docker only for this build; cloud/Terraform deploy explicitly out of scope

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build the entire remaining platform in one milestone, not a narrower slice | User wants full end-to-end coverage of PLAN.md in this pass | — Pending |
| Simulator-only market data, no Massive key | User doesn't have a Massive API key; PLAN.md already treats the simulator as the recommended default | — Pending |
| Skip cloud deployment (Terraform/App Runner) | Explicit stretch goal in PLAN.md; user wants Docker-only for this build | — Pending |
| Use the real `OPENROUTER_API_KEY` from the start (not `LLM_MOCK`) | Key already present in `.env` per user | — Pending |
| AI Integration Phase workflow toggle left off | User's explicit choice in `/gsd-settings`; framework already fixed by PLAN.md (LiteLLM/OpenRouter/Cerebras), so framework-selection research isn't needed | — Pending |
| Watchlist rows use `<div role="button">` with `tabindex`/focus-ring styling rather than semantic `<button>` | Lets the grid-column layout (ticker / price / change%) render as CSS grid children directly, keeping keyboard/AT accessibility via ARIA role instead of native button box model | ✓ Shipped Phase 1 — verified hover/focus accent-blue affordances live |
| Connection health derives from a periodic staleness tick plus real EventSource events, not `readyState` alone | A wedged-but-open SSE socket must downgrade to "Reconnecting" instead of showing a false-green "Connected" over frozen prices (T-01-12) | ✓ Shipped Phase 1 |
| Trades fill at a server-authoritative price read from `PriceCache` inside the transaction; the client can never supply a price | Matches PLAN.md's "instant fill at current market price" and closes a client-price-tampering threat (T-02-02) before it opens | ✓ Shipped Phase 2 |
| Trade bar accepts only watchlist tickers and whole-share quantities; `execute_trade()` itself stays float-typed and HTTP-agnostic | Keeps Phase 2 simple (no arbitrary-ticker lookup, no fractional-share UI) while leaving the service function ready for Phase 4's LLM-initiated trades to call directly | ✓ Shipped Phase 2 |
| Concurrent trades serialized via SQLite `BEGIN IMMEDIATE` before the first read | Prevents a lost-update race where two near-simultaneous trades validate against stale cash/position state (T-02-03/T-02-07) | ✓ Shipped Phase 2 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-16 after Phase 2*
