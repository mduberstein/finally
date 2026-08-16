# Roadmap: FinAlly — AI Trading Workstation

## Overview

FinAlly starts from a tested-but-unwired market data package and ends as a single-container Bloomberg-style trading terminal with an AI copilot. Each phase is a vertical MVP slice: something the user can open in a browser and use end-to-end, not a technical layer. Phase 1 turns the existing `backend/app/market/*` package into a running app with a database and a dark terminal frontend streaming live prices. Phase 2 makes the money real — buy, sell, and watch the portfolio respond. Phase 3 completes the visual terminal (heatmap, P&L chart, sparklines, main chart) and gives the user control over what they watch. Phase 4 drops in the AI copilot that can analyze and trade on the user's behalf. Phase 5 packages the whole thing so anyone can launch it with one command, proven by an E2E suite.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Live Streaming Terminal** - Wire the existing market feed into a running FastAPI app with a database and a dark terminal UI showing live-streaming prices (completed 2026-08-15)
- [ ] **Phase 2: Trading & Portfolio** - User buys and sells shares at live prices and watches cash, positions, and total value respond
- [ ] **Phase 3: Visual Terminal & Watchlist Control** - Heatmap, P&L chart, sparklines, main chart, and full watchlist curation in the complete terminal layout
- [ ] **Phase 4: AI Copilot** - Chat assistant that analyzes the portfolio and executes trades and watchlist changes through natural language
- [ ] **Phase 5: One-Command Launch** - Single Docker image, start/stop scripts, persistent data, and a passing Playwright E2E suite

## Phase Details

### Phase 1: Live Streaming Terminal

**Goal**: A user opens a browser and watches ten default tickers stream live prices in a dark trading terminal
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: MARKET-01, MARKET-02, MARKET-03, MARKET-04, WATCH-01, INFRA-01, UI-01
**Success Criteria** (what must be TRUE):

  1. User visits `localhost:8000` and sees a dark terminal-style watchlist listing AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX with prices
  2. Prices update continuously without a page reload; each change briefly flashes green on an uptick or red on a downtick and fades back within about half a second
  3. The header connection dot reads green while the stream is healthy, yellow while reconnecting, and red when the stream is down — and recovers to green on its own after the backend comes back
  4. Starting the app against an empty `db/` directory creates and seeds the database automatically; restarting against an existing one reuses it without wiping data

**Plans**: 4/4 plans executed

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Walking-skeleton tracer: seeded SQLite through FastAPI to a streaming browser page

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Dark terminal theme, Header/Watchlist/WatchlistRow decomposition, frontend test runner

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Price flash green on uptick, red on downtick, fading over ~500ms
- [x] 01-04-PLAN.md — Three-state connection indicator with automatic recovery

**UI hint**: yes

### Phase 2: Trading & Portfolio

**Goal**: A user can buy and sell shares at live market prices and see the portfolio respond immediately
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, PORT-10, UI-03, TEST-01
**Success Criteria** (what must be TRUE):

  1. A fresh user starts with $10,000 cash shown in the header
  2. User types a ticker and quantity in the trade bar, clicks buy, and the trade fills instantly at the current price — cash drops and the position appears in the positions table with no confirmation dialog
  3. Selling returns cash at the live price and reduces or removes the position
  4. Buying beyond available cash, or selling more shares than owned, is refused with a clear on-screen error and leaves cash and positions unchanged
  5. The positions table shows ticker, quantity, average cost, current price, unrealized P&L, and % change, and the header total value (cash + positions) moves with every price tick

**Plans**: 3 plans

Plans:
**Wave 1**

- [ ] 02-01-PLAN.md — Tracer: a Buy travels from the trade bar to SQLite and back as a live header total

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 02-02-PLAN.md — Sell, the oversell guard, the full TEST-01 backend suite, and the inline error surface
- [ ] 02-03-PLAN.md — Positions table with live price, unrealized P&L, and % change

**UI hint**: yes

### Phase 3: Visual Terminal & Watchlist Control

**Goal**: A user can see the whole portfolio at a glance and curate which tickers the terminal tracks
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: PORT-08, PORT-09, WATCH-02, WATCH-03, WATCH-04, WATCH-05, UI-02, UI-04, TEST-03
**Success Criteria** (what must be TRUE):

  1. User sees a portfolio heatmap where each position is a rectangle sized by its share of the portfolio and colored green for profit or red for loss
  2. User sees a P&L chart of total portfolio value over time that gains a new point every 30 seconds and immediately after each trade
  3. Each watchlist row grows a sparkline that fills in progressively from the live stream after page load
  4. User can add and remove watchlist tickers; added tickers begin streaming prices, removed ones disappear from the grid
  5. Clicking a watchlist row loads that ticker into the main chart area, and the full layout — watchlist, main chart, heatmap, P&L chart, positions table, trade bar, chat panel, header — fits a wide desktop screen without excess scrolling and stays usable at tablet width

**Plans**: TBD
**UI hint**: yes

### Phase 4: AI Copilot

**Goal**: A user can converse with an AI assistant that analyzes the portfolio and acts on it through natural language
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, TEST-02
**Success Criteria** (what must be TRUE):

  1. User asks how their portfolio is doing and gets a concise, data-grounded reply referencing their actual positions, cash, concentration, and P&L
  2. User tells the assistant to buy or sell; a loading indicator shows while it thinks, then the trade executes with no confirmation dialog and the positions table, cash, header value, and chat transcript all reflect it
  3. User asks the assistant to add or drop a ticker and the watchlist changes on screen
  4. A trade the assistant cannot fill (insufficient cash, overselling) comes back as a plain-language explanation in the chat, with the portfolio left unchanged
  5. Reloading the page restores the full conversation history, and running with `LLM_MOCK=true` returns deterministic replies with no external API call

**Plans**: TBD
**UI hint**: yes

### Phase 5: One-Command Launch

**Goal**: Anyone can run the whole workstation with one command and keep their data across restarts
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: INFRA-02, INFRA-03, INFRA-04, TEST-04
**Success Criteria** (what must be TRUE):

  1. From a clean checkout, running `scripts/start_mac.sh` (or the Windows equivalent, or `docker compose up`) builds and starts one container and serves the complete working terminal at `localhost:8000`
  2. Stopping the app and starting it again preserves cash, positions, trade history, watchlist, and chat history
  3. The Playwright E2E suite runs against the container with `LLM_MOCK=true` and passes: fresh start, add/remove ticker, buy and sell, AI-executed trade, and SSE reconnection
  4. Running the start and stop scripts repeatedly is safe — no duplicate containers, no lost volume

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Live Streaming Terminal | 4/4 | Complete    | 2026-08-15 |
| 2. Trading & Portfolio | 0/3 | Planned      | - |
| 3. Visual Terminal & Watchlist Control | 0/TBD | Not started | - |
| 4. AI Copilot | 0/TBD | Not started | - |
| 5. One-Command Launch | 0/TBD | Not started | - |

## Requirement Coverage

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1. Live Streaming Terminal | MARKET-01, MARKET-02, MARKET-03, MARKET-04, WATCH-01, INFRA-01, UI-01 | 7 |
| 2. Trading & Portfolio | PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, PORT-10, UI-03, TEST-01 | 10 |
| 3. Visual Terminal & Watchlist Control | PORT-08, PORT-09, WATCH-02, WATCH-03, WATCH-04, WATCH-05, UI-02, UI-04, TEST-03 | 9 |
| 4. AI Copilot | CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, TEST-02 | 10 |
| 5. One-Command Launch | INFRA-02, INFRA-03, INFRA-04, TEST-04 | 4 |

**Total: 40/40 v1 requirements mapped. No orphans, no duplicates.**

## Notes

- **Do not rebuild the market data layer.** `backend/app/market/*` (interface, simulator, Massive client, feed, cache, stream router, factory) already exists and is tested. Phase 1 wires it in via a FastAPI lifespan handler: `create_source()` → `MarketFeed.start()` → `PriceCache`, and mounts `create_stream_router(cache)`.
- **Read prices only through `PriceCache`.** Calling a source's `fetch()` from portfolio, trade, or chat code is a documented anti-pattern (`.planning/codebase/ARCHITECTURE.md`). Trade execution and portfolio valuation must read `cache.get(ticker)` / `cache.snapshot()`.
- **Call `MarketFeed.start()` exactly once** per app lifespan and `await feed.stop()` on shutdown.
- **LLM calls follow the `cerebras-inference` project skill**: LiteLLM `completion()` with `model="openrouter/openai/gpt-oss-120b"`, `extra_body={"provider": {"order": ["cerebras"]}}`, `response_format=<pydantic model>`, `reasoning_effort="low"`.
- **Simulator only** for this build — no `MASSIVE_API_KEY`. The Massive client stays as an alternate implementation but is not exercised.
- **Single hardcoded `user_id="default"`** across every table and route.
