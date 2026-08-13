# External Integrations

**Analysis Date:** 2026-08-12

## APIs & External Services

**Market Data (Dual Implementation):**
- Massive (formerly Polygon.io) REST Snapshot API - Optional real-time market data
  - Endpoint: `https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers`
  - SDK/Client: None; uses raw `httpx.AsyncClient` for async compatibility
  - Auth: Bearer token via `Authorization` header
  - Env var: `MASSIVE_API_KEY`
  - Implementation: `backend/app/market/massive.py` (class `MassiveSource`)
  - Fallback behavior: If HTTP 401/403, falls back to simulator; if HTTP 429, doubles poll interval
  - Default poll interval: 15 seconds (overridable via `MARKET_POLL_INTERVAL`)

- Built-in Market Simulator - Default if no Massive API key
  - No external dependency; pure Python implementation
  - Geometric Brownian Motion with mean reversion (Ornstein-Uhlenbeck process in log space)
  - Configurable per-ticker volatility and correlation
  - Random "drama events" for 2-5% jumps
  - Implementation: `backend/app/market/simulator.py` (class `SimulatorSource`)
  - Seed support: `MARKET_SEED` env var for deterministic testing

**AI/LLM Chat (Planned, Not Yet Implemented):**
- OpenRouter API - For LLM inference
  - Provider: Cerebras (via openrouter/openai/gpt-oss-120b model per PLAN.md)
  - SDK/Client: LiteLLM (not yet added to dependencies)
  - Auth: Bearer token via environment variable
  - Env var: `OPENROUTER_API_KEY`
  - Response format: Structured JSON with schema for `message`, `trades[]`, `watchlist_changes[]`
  - Implementation location: `backend/app/api/chat.py` (not yet created)
  - Mock mode: When `LLM_MOCK=true`, returns deterministic responses (for E2E testing)

## Data Storage

**Databases:**
- SQLite (planned, not yet implemented)
  - Location: `/app/db/finally.db` (in container); volume-mounted at `finally-data:/app/db`
  - Client: sqlite3 (Python standard library) or via SQLAlchemy ORM (decision pending)
  - Schema location: `backend/db/` (schema SQL and initialization code)
  - Tables planned:
    - `users_profile` - Cash balance, timestamps
    - `watchlist` - User's watched tickers
    - `positions` - Current holdings (quantity, avg cost)
    - `trades` - Trade history log
    - `portfolio_snapshots` - Portfolio value over time (recorded every 30s)
    - `chat_messages` - Conversation history with executed trade/watchlist actions

**File Storage:**
- Local filesystem only - Frontend static exports served by FastAPI

**Caching:**
- In-memory price cache - Holds latest/previous price per ticker
  - Implementation: `backend/app/market/cache.py` (class `PriceCache`)
  - No external cache service (Redis not needed for single-user)

## Authentication & Identity

**Auth Provider:**
- None currently - Single-user mode, hardcoded `user_id="default"`
- Future: All schema tables include `user_id` column for multi-user support without migration

## Monitoring & Observability

**Error Tracking:**
- Not detected - No Sentry, Rollbar, or similar integration yet

**Logs:**
- Python `logging` module - Standard library, structured via logger names per module
- Demo dashboard: Rich CLI for market data visualization (`market_data_demo.py`)

## CI/CD & Deployment

**Hosting:**
- Docker (single container, single port 8000)
- Deployment target: AWS App Runner, Render, or any container platform
- Terraform for App Runner (optional, not yet in repo)

**CI Pipeline:**
- GitHub Actions (workflows in `.github/workflows/`)
- Workflow files:
  - `claude-code-review.yml` - Claude code review integration
  - `claude.yml` - General Claude-driven CI tasks

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` - OpenRouter API key for AI chat (once LLM integration is implemented)

**Optional env vars:**
- `MASSIVE_API_KEY` - Massive API key for real market data
- `MARKET_POLL_INTERVAL` - Custom poll interval for Massive (default 15s)
- `MARKET_SEED` - Seed for simulator RNG (deterministic testing)
- `LLM_MOCK` - Set to `true` for mock LLM responses (E2E testing)

**Secrets location:**
- `.env` file at project root (gitignored)
- Read by `backend/app/market/factory.py` and planned LLM integration
- Docker: passed via `--env-file .env` flag

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- SSE stream endpoint: `GET /api/stream/prices` - Server pushes price updates to connected clients via Server-Sent Events
  - No external webhooks; one-way push to browser clients

## API Endpoints (Current & Planned)

**Market Data (Implemented):**
- `GET /api/stream/prices` - SSE stream of price updates (implemented in `backend/app/market/stream.py`)

**Portfolio (Planned):**
- `GET /api/portfolio` - Current positions, cash, total value, P&L
- `POST /api/portfolio/trade` - Execute trade: `{ticker, quantity, side}`
- `GET /api/portfolio/history` - Portfolio snapshots over time

**Watchlist (Planned):**
- `GET /api/watchlist` - Current watchlist with latest prices
- `POST /api/watchlist` - Add ticker: `{ticker}`
- `DELETE /api/watchlist/{ticker}` - Remove ticker

**Chat (Planned):**
- `POST /api/chat` - Send message; returns JSON with conversational response + auto-executed actions

**System:**
- `GET /api/health` - Health check (for Docker/deployment)

---

*Integration audit: 2026-08-12*
