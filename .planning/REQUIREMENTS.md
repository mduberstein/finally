# Requirements: FinAlly — AI Trading Workstation

**Defined:** 2026-08-12
**Core Value:** A user can watch live prices stream, trade a simulated portfolio, and have an AI assistant execute trades and manage the watchlist through natural language — all in one fluid, visually polished terminal-style interface.

## v1 Requirements

Requirements for the full remaining build. Each maps to roadmap phases. Market data source code already exists (`backend/app/market/*`) — the MARKET category covers wiring it into a running app, not rebuilding it.

### Market Data & Streaming

- [ ] **MARKET-01**: Watchlist prices update live in the UI via the SSE stream at `/api/stream/prices`, sourced from the existing `PriceCache`/`MarketFeed`
- [ ] **MARKET-02**: Prices flash green on an uptick and red on a downtick, fading over ~500ms
- [ ] **MARKET-03**: A connection status indicator in the header shows green (connected), yellow (reconnecting), or red (disconnected)
- [ ] **MARKET-04**: FastAPI app starts `MarketFeed` with the simulator source on lifespan startup and stops it cleanly on shutdown

### Portfolio

- [ ] **PORT-01**: User starts with $10,000 in virtual cash
- [ ] **PORT-02**: User can buy shares of a ticker at the current market price — instant fill, no fees, no confirmation dialog
- [ ] **PORT-03**: User can sell shares they own at the current market price — instant fill
- [ ] **PORT-04**: Buying with insufficient cash is rejected with a clear error
- [ ] **PORT-05**: Selling more shares than owned is rejected with a clear error
- [ ] **PORT-06**: User can view a positions table: ticker, quantity, avg cost, current price, unrealized P&L, % change
- [ ] **PORT-07**: User can view total portfolio value (cash + position value) updating live in the header
- [ ] **PORT-08**: User can view a portfolio heatmap (treemap) sized by position weight, colored by P&L
- [ ] **PORT-09**: User can view a P&L chart of total portfolio value over time, recorded every 30s and after each trade
- [ ] **PORT-10**: Trade history is recorded append-only in the trades table

### Watchlist

- [ ] **WATCH-01**: User sees 10 default watchlist tickers on first launch (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)
- [ ] **WATCH-02**: User can add a ticker to the watchlist
- [ ] **WATCH-03**: User can remove a ticker from the watchlist
- [ ] **WATCH-04**: Each watchlist row shows a sparkline mini-chart accumulated from the SSE stream since page load
- [ ] **WATCH-05**: Clicking a watchlist ticker selects it in the main chart area

### AI Chat

- [ ] **CHAT-01**: User can send a chat message and receive a complete structured JSON response (message + executed actions) from the LLM
- [ ] **CHAT-02**: The LLM assistant can analyze portfolio composition, risk concentration, and P&L when asked
- [ ] **CHAT-03**: The LLM assistant can auto-execute trades it recommends and the user agrees to, without a confirmation dialog
- [ ] **CHAT-04**: The LLM assistant can add/remove watchlist tickers through natural language
- [ ] **CHAT-05**: Failed LLM-initiated trades (e.g. insufficient cash) surface as an error the assistant explains back to the user
- [ ] **CHAT-06**: Chat conversation history persists across page reloads (`chat_messages` table)
- [ ] **CHAT-07**: A loading indicator shows while waiting for the LLM response
- [ ] **CHAT-08**: LLM calls use LiteLLM → OpenRouter → Cerebras (`gpt-oss-120b`) with structured outputs, per the `cerebras-inference` skill
- [ ] **CHAT-09**: Setting `LLM_MOCK=true` returns deterministic mock responses for testing

### Frontend & Visual Design

- [ ] **UI-01**: Dark trading-terminal visual theme (near-black backgrounds, muted borders, brand accent colors) applied consistently across the app
- [ ] **UI-02**: Layout includes watchlist panel, main chart area, portfolio heatmap, P&L chart, positions table, trade bar, AI chat panel, and header — all visible without excess scrolling on a wide desktop screen
- [ ] **UI-03**: Trade bar lets the user enter ticker/quantity and submit buy or sell with one click
- [ ] **UI-04**: App is usable (not broken) on a tablet-width viewport, optimized for desktop

### Infrastructure & Deployment

- [ ] **INFRA-01**: SQLite database lazily initializes schema and seeds default data on first run if the DB file doesn't exist
- [ ] **INFRA-02**: Single multi-stage Dockerfile builds the Next.js static export and the FastAPI backend into one image serving port 8000
- [ ] **INFRA-03**: `docker-compose.yml` and `scripts/start_mac.sh` / `scripts/stop_mac.sh` (and Windows equivalents) let the user launch/stop the app with one command
- [ ] **INFRA-04**: SQLite file persists across container restarts via a volume mount at `db/finally.db`

### Testing

- [ ] **TEST-01**: Backend unit tests cover trade execution, P&L math, and edge cases (insufficient cash, overselling)
- [ ] **TEST-02**: Backend unit tests cover LLM structured-output parsing, including malformed responses
- [ ] **TEST-03**: Frontend unit tests cover price flash animation, watchlist CRUD, and portfolio display calculations
- [ ] **TEST-04**: Playwright E2E suite (`test/`, `LLM_MOCK=true`) covers: fresh start, add/remove ticker, buy/sell trade flow, AI chat trade execution, SSE reconnection

## v2 Requirements

None — this build covers the full PLAN.md v1 scope in one milestone.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real Massive/Polygon market data | No Massive API key available; simulator is the default per PLAN.md. Massive client code stays in the codebase but isn't exercised in production for this build |
| Cloud deployment (Terraform/App Runner) | Explicit stretch goal in PLAN.md; user wants Docker-only for this build |
| Multi-user auth / login | PLAN.md is explicitly zero-auth, single hardcoded `user_id="default"` |
| Limit orders / order book | Market orders only, per PLAN.md's simplicity rationale |
| Trade confirmation dialogs | Instant-fill by design, including LLM-initiated trades |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MARKET-01 | TBD | Pending |
| MARKET-02 | TBD | Pending |
| MARKET-03 | TBD | Pending |
| MARKET-04 | TBD | Pending |
| PORT-01 | TBD | Pending |
| PORT-02 | TBD | Pending |
| PORT-03 | TBD | Pending |
| PORT-04 | TBD | Pending |
| PORT-05 | TBD | Pending |
| PORT-06 | TBD | Pending |
| PORT-07 | TBD | Pending |
| PORT-08 | TBD | Pending |
| PORT-09 | TBD | Pending |
| PORT-10 | TBD | Pending |
| WATCH-01 | TBD | Pending |
| WATCH-02 | TBD | Pending |
| WATCH-03 | TBD | Pending |
| WATCH-04 | TBD | Pending |
| WATCH-05 | TBD | Pending |
| CHAT-01 | TBD | Pending |
| CHAT-02 | TBD | Pending |
| CHAT-03 | TBD | Pending |
| CHAT-04 | TBD | Pending |
| CHAT-05 | TBD | Pending |
| CHAT-06 | TBD | Pending |
| CHAT-07 | TBD | Pending |
| CHAT-08 | TBD | Pending |
| CHAT-09 | TBD | Pending |
| UI-01 | TBD | Pending |
| UI-02 | TBD | Pending |
| UI-03 | TBD | Pending |
| UI-04 | TBD | Pending |
| INFRA-01 | TBD | Pending |
| INFRA-02 | TBD | Pending |
| INFRA-03 | TBD | Pending |
| INFRA-04 | TBD | Pending |
| TEST-01 | TBD | Pending |
| TEST-02 | TBD | Pending |
| TEST-03 | TBD | Pending |
| TEST-04 | TBD | Pending |

**Coverage:**
- v1 requirements: 38 total
- Mapped to phases: 0
- Unmapped: 38 ⚠️ (roadmap creation pending)

---
*Requirements defined: 2026-08-12*
*Last updated: 2026-08-12 after initial definition*
