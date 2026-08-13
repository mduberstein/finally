<!-- refreshed: 2026-08-12 -->
# Codebase Concerns

**Analysis Date:** 2026-08-12

## Critical Blockers

### Missing FastAPI Application Entry Point

**Issue:** No `main.py` or `app.py` exists in `backend/app/`. The codebase contains only the market data components (`backend/app/market/`), with no actual FastAPI application instance, route registration, or server startup logic.

**Files:** `backend/app/` (empty except for `__init__.py`), `backend/app/market/stream.py` (defines router but it's never integrated)

**Impact:** 
- The backend cannot run. There's nothing to serve.
- The `/api/stream/prices` SSE endpoint is defined but has no parent application.
- No ability to test or demo the application end-to-end.

**Fix approach:**
- Create `backend/app/main.py` with FastAPI instance, startup/shutdown hooks, router registration
- Wire the market stream router created in `stream.py`
- Set up lifespan management for MarketFeed startup/stop
- Add uvicorn entry point or create `__main__.py` for module execution

---

### Missing Database Layer

**Issue:** The plan specifies a SQLite database with schema for users_profile, watchlist, positions, trades, portfolio_snapshots, and chat_messages. No database code exists.

**Files:** None — completely missing

**Impact:**
- Cannot persist portfolio state, trade history, or chat messages
- No schema migrations or lazy initialization
- Portfolio data will be lost on app restart

**Fix approach:**
- Create `backend/app/db/` directory with:
  - `schema.py` — table definitions and initialization logic
  - `models.py` — SQLAlchemy ORM models or dataclass wrappers
  - Connection pooling and lifecycle management
- Add SQLAlchemy or similar ORM to `pyproject.toml` dependencies
- Implement lazy initialization in app startup (check for tables, create if missing)

---

### Missing Portfolio & Trading Logic

**Issue:** No implementation of:
- Trade execution (buy/sell orders)
- Position tracking
- Cash balance management
- P&L calculations
- Portfolio value snapshots

**Files:** None — completely missing

**Impact:**
- No core functionality. The entire app collapses without this.
- Cannot execute trades, calculate profits/losses, or track holdings.

**Fix approach:**
- Create `backend/app/portfolio/` with:
  - `models.py` — Trade, Position, PortfolioState dataclasses
  - `service.py` — Trade execution, P&L calculation, position updates
  - `validation.py` — Enforce cash/share constraints, prevent overselling
- Implement atomic transaction handling for trades
- Add portfolio snapshot recording (every 30s and after each trade)

---

### Missing API Endpoints

**Issue:** Only `/api/stream/prices` (SSE) is implemented. Missing all core endpoints:
- `/api/portfolio` (GET) — positions, cash, total value, unrealized P&L
- `/api/portfolio/trade` (POST) — execute buy/sell
- `/api/portfolio/history` (GET) — portfolio value snapshots for P&L chart
- `/api/watchlist` (GET/POST) — manage watched tickers
- `/api/watchlist/{ticker}` (DELETE) — remove ticker
- `/api/chat` (POST) — LLM integration with structured output
- `/api/health` (GET) — health check

**Files:** None — completely missing

**Impact:** 
- No functional API surface.
- Frontend cannot interact with the backend.

**Fix approach:**
- Create `backend/app/api/` directory with:
  - `routers/portfolio.py` — Trade execution, portfolio state
  - `routers/watchlist.py` — CRUD operations on watchlist
  - `routers/chat.py` — LLM integration
  - `routers/health.py` — Basic health check
- Register all routers in main application
- Add Pydantic models for request/response validation

---

### Missing LLM Integration

**Issue:** No code for LLM chat, structured output parsing, or auto-execution of LLM-suggested trades.

**Files:** None — completely missing

**Impact:**
- Chat feature unusable.
- No AI copilot capability (core feature of the app).

**Fix approach:**
- Add `litellm>=1.0.0` to dependencies (currently missing)
- Create `backend/app/llm/` with:
  - `client.py` — LiteLLM OpenRouter configuration and calls
  - `schema.py` — Pydantic models for structured output (message, trades[], watchlist_changes[])
  - `service.py` — Orchestration: load portfolio context, call LLM, parse response, validate trades
- Implement trade validation within LLM response handling (do not auto-execute invalid trades)
- Handle `LLM_MOCK=true` environment variable for testing

---

### Missing Frontend

**Issue:** No `frontend/` directory. The entire UI/browser layer is unimplemented.

**Files:** None — completely missing

**Impact:**
- No user interface.
- Cannot access the application from a browser.

**Fix approach:**
- Create `frontend/` as a Next.js TypeScript project with:
  - Page layout and main component structure
  - Watchlist grid component with price flash animations
  - Chart components (mini sparklines, main ticker chart, P&L chart, heatmap)
  - Portfolio positions table
  - Trade input bar
  - AI chat panel
- SSE client connection to `/api/stream/prices` using native EventSource API
- Responsive design optimized for desktop, functional on tablet

---

## Missing Infrastructure

### No Docker Setup

**Issue:** No `Dockerfile` or `docker-compose.yml`. The plan specifies a multi-stage build and single-container deployment.

**Files:** None

**Impact:**
- Cannot build or run the application in containers.
- No production-ready deployment path.

**Fix approach:**
- Create `Dockerfile` with:
  - Stage 1: Node 20 slim → build Next.js static export
  - Stage 2: Python 3.12 slim → install uv, copy backend, install deps, copy frontend build, expose 8000, CMD uvicorn
- Optional: `docker-compose.yml` for convenience
- Test build and verify single-container architecture works

---

### No Start/Stop Scripts

**Issue:** `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1` are missing.

**Files:** None

**Impact:**
- Users cannot easily run the application with `./scripts/start_mac.sh`
- Deployment instructions are incomplete.

**Fix approach:**
- Create shell scripts that:
  - Build Docker image (or skip if already built)
  - Run container with volume mount for db persistence
  - Print access URL and optionally open browser
  - Handle cleanup on stop (remove container but preserve volume)

---

## Dependency Gaps

### Missing Core Dependencies

**Issue:** `pyproject.toml` is missing several critical packages:
- `litellm` — LLM API integration (required for chat feature)
- `python-dotenv` — Environment variable loading from `.env` (needed if `.env` file is used at runtime rather than passed to Docker)
- Database library — No ORM or explicit `sqlite3` setup (Python's sqlite3 is built-in, but using raw SQL is error-prone; SQLAlchemy recommended)
- `pydantic` — Request/response validation (implicit via FastAPI, but should be explicit)

**Files:** `backend/pyproject.toml`

**Impact:**
- LLM feature cannot be implemented without litellm
- No structured input validation beyond FastAPI's built-in

**Fix approach:**
```
Add to dependencies:
- "litellm>=1.0.0"
- "sqlalchemy>=2.0.0"  (or "tortoise-orm" for async ORM)
- "pydantic>=2.0.0"  (already implicit, make explicit)
- "python-dotenv>=1.0.0"  (if needed at runtime)
```

---

## Test Coverage Gaps

### No API Endpoint Tests

**Issue:** Only market data components have tests (`backend/tests/market/`). Zero tests for:
- Portfolio endpoints (trade execution, position retrieval)
- Watchlist CRUD
- Chat endpoint and LLM integration
- Health check

**Files:** `backend/tests/` — only `market/` subdirectory has tests

**Impact:**
- Cannot verify API correctness during development.
- Regressions in trading logic go undetected.

**Priority:** High — portfolio and chat are core features.

**Fix approach:**
```
Create backend/tests/:
├── test_api.py  (or split per module)
│   ├── test_portfolio_endpoints.py
│   ├── test_watchlist_endpoints.py
│   ├── test_chat_endpoints.py
│   └── test_health.py
├── test_trading.py  (trade execution, P&L, validation)
├── test_db.py  (database initialization, queries)
└── test_llm.py  (structured output parsing, LLM mock responses)
```

---

### No Database Tests

**Issue:** Once database layer is implemented, must test:
- Schema initialization and migrations
- CRUD operations on positions, trades, watchlist
- Transaction isolation and atomicity for trades

**Files:** None yet; will be needed in `backend/tests/`

**Priority:** High — data correctness is critical.

---

### No Frontend Tests

**Issue:** No tests for React components, API client, or SSE connection handling.

**Files:** None

**Impact:**
- UI bugs only discovered by manual testing.
- Refactors are risky.

**Priority:** Medium — E2E tests can provide coverage if component tests lag.

---

### No E2E Tests

**Issue:** The plan mentions `test/` directory with Playwright E2E tests and `docker-compose.test.yml`, but this doesn't exist.

**Files:** None

**Impact:**
- Cannot verify full system behavior without manual clicking.
- Cannot test SSE connection resilience or reconnection.

**Priority:** Medium-High — valuable for catching integration issues.

**Fix approach:**
```
Create test/:
├── docker-compose.test.yml  (app container + Playwright container)
├── playwright.config.ts
└── tests/
    ├── e2e/
    │   ├── market-stream.spec.ts
    │   ├── portfolio-trading.spec.ts
    │   ├── chat-integration.spec.ts
    │   └── watchlist-management.spec.ts
```

---

## Known Test Execution Issue

### Pytest Requires `--extra dev` Flag

**Issue:** Running `uv run pytest` without specifying the `dev` extra uses Anaconda's pytest and lacks `pytest-asyncio`, causing silent test failures.

**Files:** `backend/pyproject.toml` (noted in project memory)

**Impact:**
- Developers who run `uv run pytest` get no pytest-asyncio plugin, and async tests silently use a standard event loop, potentially causing false passes/failures.

**Workaround:** Run `uv run --extra dev pytest` instead.

**Fix approach:**
- Document in `backend/README.md` that dev dependencies are required for testing
- Consider moving pytest-asyncio to main dependencies if tests are run frequently in CI
- Add a `pytest` script in pyproject.toml: `pytest = "pytest --extra dev"` (if uv supports it)

---

## Scaling & Performance Concerns

### SSE Stream Efficiency

**Issue:** In `backend/app/market/stream.py`, the price event generator loops every 0.5s and yields the entire snapshot from the cache, filtering for changes. With many tickers, this becomes inefficient.

```python
async def price_events(cache: PriceCache) -> AsyncIterator[dict]:
    ...
    while True:
        await asyncio.sleep(STREAM_INTERVAL)  # 0.5s loop
        for update in cache.snapshot():       # Full snapshot every tick
            if seen.get(update.ticker) != update.price:
                yield _format(update)
```

**Impact:**
- If the watchlist grows to 100+ tickers, the loop iterates over all of them every 0.5s.
- For a single stream connection this is fine, but with many concurrent clients, CPU usage grows linearly.

**Priority:** Low for MVP (10 default tickers), High if scaling beyond 50 tickers.

**Fix approach:**
- Cache maintains a "changed tickers" set; only iterate those instead of full snapshot
- Or use a priority queue of pending updates and drain it in the loop

---

### Market Feed Task Resilience

**Issue:** `backend/app/market/feed.py` catches exceptions broadly but does not implement circuit breaker or maximum retry attempts. An API that permanently fails (e.g., wrong key) will spam logs forever.

**Files:** `backend/app/market/feed.py`, lines 85–109

**Current behavior:**
- HTTP 401/403 → fallback to simulator (good)
- HTTP 429 → exponential backoff to 60s ceiling (good)
- Other exceptions → log and continue with stale cache (acceptable but could be noisy)

**Concern:** Repeated logging could flood logs if an API is unavailable for hours.

**Priority:** Low for MVP. Consider adding a circuit breaker in production.

---

### Database Locking Under High Trade Volume

**Issue:** Once the database is implemented, SQLite's locking model (single writer) could become a bottleneck if many users trade simultaneously (multi-user future).

**Files:** Not yet implemented; concern for later phases.

**Priority:** Not relevant for MVP (single user). Flag for when multi-user support is added.

---

## Architectural Debt & Design Risks

### Hardcoded Single-User Model

**Issue:** The `user_id` field defaults to `"default"` everywhere. While the schema supports multi-user, no auth layer exists, and middleware/guards to enforce user isolation are missing.

**Files:**
- `PLAN.md` section 7 (Database schema design)
- Will be evident in all future database and API code

**Risk:** If multi-user is added without proper auth/isolation logic, users can view/modify each other's portfolios.

**Mitigation:** 
- Document clearly that single-user mode is hardcoded
- Create auth middleware stub before adding multi-user
- Add user_id extraction and validation to every endpoint

---

### No Error Response Standardization

**Issue:** No error response format defined. Different endpoints will likely return different error shapes (400, 422, 500, etc.) without a common structure.

**Files:** All future endpoint code

**Impact:** Frontend must handle multiple error formats; inconsistent user experience.

**Fix approach:**
```python
# Define a common error response in backend/app/api/schema.py
@dataclass
class ErrorResponse:
    detail: str
    code: str  # e.g., "INSUFFICIENT_CASH", "UNKNOWN_TICKER"
    status: int
```

---

### No Input Validation Framework

**Issue:** While Pydantic (via FastAPI) provides some validation, domain-specific rules (e.g., "sell quantity ≤ owned quantity") are not centralized.

**Files:** Will be scattered across endpoint handlers and service code once written

**Impact:** Validation logic duplicated; risk of inconsistent enforcement.

**Fix approach:**
- Create `backend/app/api/validation.py` with custom validators
- Apply uniformly via Pydantic `field_validator` or service layer

---

## Documentation & Reference Gaps

### No Backend README

**Issue:** `backend/README.md` exists but is likely minimal. Backend developers need:
- How to set up the dev environment
- How to run tests (with the `--extra dev` caveat)
- How to run the market data demo
- Development server startup
- Code structure and module responsibilities

**Files:** `backend/README.md`

**Impact:** Onboarding friction for new agents/developers.

**Fix approach:**
- Expand README with setup steps, examples, test invocation

---

### No `.env.example` File

**Issue:** `.env` exists but is gitignored. No `.env.example` shows required variables or defaults.

**Files:** No `.env.example`

**Impact:** Users don't know what environment variables to set or what they do.

**Fix approach:**
- Create `.env.example` with all variables and descriptions:
  ```
  OPENROUTER_API_KEY=your-key-here
  MASSIVE_API_KEY=  # leave empty to use simulator
  LLM_MOCK=false
  MARKET_SEED=  # leave empty for random
  MARKET_POLL_INTERVAL=15
  ```

---

## Summary of Blockers

| Concern | Type | Priority | Estimated Effort |
|---------|------|----------|------------------|
| Missing FastAPI app | Critical | Blocker | 2-3 hrs |
| Missing database layer | Critical | Blocker | 4-6 hrs |
| Missing portfolio/trading | Critical | Blocker | 6-8 hrs |
| Missing API endpoints | Critical | Blocker | 4-6 hrs |
| Missing LLM integration | Critical | Blocker | 3-4 hrs |
| Missing frontend | Critical | Blocker | 12-15 hrs |
| Missing Docker | High | Blocker | 1-2 hrs |
| Missing scripts | High | Blocker | 0.5-1 hr |
| Missing dependencies | High | Blocker | 0.5 hr |
| Test coverage gaps (API) | High | Non-blocker | 4-6 hrs |
| E2E tests | Medium | Non-blocker | 4-6 hrs |
| SSE efficiency | Low | Non-blocker | 1-2 hrs (post-MVP) |
| Error standardization | Medium | Non-blocker | 1 hr |

---

*Concerns audit: 2026-08-12*
