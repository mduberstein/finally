# Codebase Structure

**Analysis Date:** 2026-08-12

## Directory Layout

```
finally/
├── .claude/                 # Claude Code configuration and project metadata
├── .planning/               # Project documentation for agents
│   ├── codebase/            # Architecture and structure (THIS DIRECTORY)
│   ├── PLAN.md              # Project specification and vision
│   ├── MARKET_DATA_SUMMARY.md # Market data subsystem completion summary
│   └── archive/             # Superseded design docs (reference only)
├── backend/                 # FastAPI uv project (Python)
│   ├── app/                 # Package root
│   │   ├── market/          # Market data subsystem (COMPLETE)
│   │   │   ├── __init__.py  # Public exports
│   │   │   ├── interface.py # MarketDataSource ABC
│   │   │   ├── simulator.py # SimulatorSource (GBM)
│   │   │   ├── massive.py   # MassiveSource (REST)
│   │   │   ├── cache.py     # PriceCache in-memory store
│   │   │   ├── feed.py      # MarketFeed background task
│   │   │   ├── factory.py   # create_source() seam
│   │   │   ├── stream.py    # SSE endpoint factory
│   │   │   ├── models.py    # Quote, PriceUpdate dataclasses
│   │   │   └── seed_prices.py # Per-ticker profiles
│   ├── tests/               # Test suite root
│   │   ├── conftest.py      # pytest fixtures (env cleanup)
│   │   └── market/          # Market data tests (101 tests, 99% coverage)
│   │       ├── test_models.py
│   │       ├── test_interface.py
│   │       ├── test_cache.py
│   │       ├── test_feed.py
│   │       ├── test_simulator.py
│   │       ├── test_massive.py
│   │       ├── test_factory.py
│   │       ├── test_seed_prices.py
│   │       └── test_stream.py
│   ├── archive/             # Old implementations (not active)
│   ├── pyproject.toml       # uv project config, dependencies, pytest settings
│   ├── uv.lock              # Locked dependency versions
│   └── README.md            # Backend setup and market data public API
├── frontend/                # (NOT YET IMPLEMENTED)
│   │                         # Will be Next.js static export
├── planning/                # (see above)
├── scripts/                 # (NOT YET IMPLEMENTED)
│   │                         # Will be start/stop shell scripts
├── test/                    # (NOT YET IMPLEMENTED)
│   │                         # Will be Playwright E2E tests
├── db/                      # (NOT YET IMPLEMENTED)
│   │                         # Runtime volume mount for SQLite
├── Dockerfile               # (NOT YET IMPLEMENTED)
├── docker-compose.yml       # (NOT YET IMPLEMENTED)
├── .env                     # Environment variables (gitignored)
├── .env.example             # (NOT YET CREATED)
├── .gitignore               # Git ignore rules
├── CLAUDE.md                # Project instructions (links to PLAN.md)
├── README.md                # Top-level project overview
└── LICENSE                  # MIT license
```

## Directory Purposes

**`backend/app/`** (Python package root)
- Purpose: FastAPI application code and domain logic
- Contains: Currently only `market/` subpackage
- Future: `portfolio/`, `trades/`, `database/`, `chat/`, `api/` subpackages

**`backend/app/market/`** (Market data subsystem)
- Purpose: Live price sourcing from simulator or Massive API, exposed via abstract interface
- Contains: All market data components (sources, cache, feed, streaming)
- Status: Complete with 101 tests, 99% coverage
- Key files:
  - `interface.py` — `MarketDataSource` ABC (one abstract method: `fetch(tickers) -> list[Quote]`)
  - `simulator.py` — GBM simulator with Ornstein-Uhlenbeck anchor pull
  - `massive.py` — Async httpx REST client for Massive snapshot endpoint
  - `cache.py` — In-memory latest/previous price store; sole owner of direction
  - `feed.py` — Background polling task with 401/403 fallback and 429 backoff
  - `factory.py` — `create_source()` environment-aware factory seam
  - `stream.py` — `create_stream_router()` SSE endpoint factory
  - `models.py` — Frozen dataclasses: `Quote`, `PriceUpdate`
  - `seed_prices.py` — Per-ticker volatility/correlation profiles for 10 default tickers

**`backend/tests/`**
- Purpose: Test suite for backend
- Contains: Mirrors package structure; currently only `market/` tests
- Pattern: `test_*.py` files, one per module plus `conftest.py`
- Run with: `uv run pytest -v --cov=app`

**`.planning/`**
- Purpose: Shared documentation for all project agents
- Contains:
  - `PLAN.md` — Full project specification (vision, UX, architecture overview, database schema, API endpoints, environment variables)
  - `MARKET_DATA_SUMMARY.md` — Market data subsystem completion summary (what's built, design decisions, usage)
  - `codebase/` — Architecture and structure docs (ARCHITECTURE.md, STRUCTURE.md)
  - `archive/` — Superseded design docs (reference only; not current)

## Key File Locations

**Entry Points:**
- FastAPI app: Not yet created; will be `backend/app/main.py` or similar
- Backend start: `uvicorn backend.app:app --host 0.0.0.0 --port 8000` (not yet wired)
- Tests: `backend/tests/` — run with `uv run pytest`

**Configuration:**
- Environment variables: `.env` (gitignored) and `.env.example` (not yet created)
- uv project: `backend/pyproject.toml` — dependencies, test config, linting rules
- pytest: `backend/pyproject.toml` — testpaths, asyncio mode, coverage settings
- ruff (linting): `backend/pyproject.toml` — E, F, I, N, W rules; line length 100

**Core Logic:**
- Market data: `backend/app/market/` (complete)
- Portfolio/trades: Not implemented; will go in `backend/app/portfolio/` or `backend/app/trading/`
- Database: Not implemented; will go in `backend/app/database/` or similar
- API routes: Not implemented; will go in `backend/app/api/` or route handlers in `main.py`
- LLM chat: Not implemented; will go in `backend/app/chat/` or similar

**Testing:**
- Market data tests: `backend/tests/market/` (101 tests, 99% coverage)
- E2E tests: `test/` (not yet created) — Playwright tests
- Test fixtures: `backend/tests/conftest.py` — autouse env cleanup fixture

## Naming Conventions

**Files:**
- Module files: `snake_case.py` (e.g., `market_data.py`, `test_models.py`)
- Test files: `test_*.py` for unit tests; E2E tests in `test/` with Playwright conventions
- Configuration: `pyproject.toml`, `.env`, `.gitignore`

**Directories:**
- Package directories: `snake_case/` with `__init__.py` (e.g., `app/market/`, `backend/app/`)
- Test directories: Mirror package structure under `tests/` (e.g., `tests/market/` for `app/market/`)
- Project directories: Descriptive names (e.g., `backend/`, `frontend/`, `planning/`, `scripts/`)

**Python Functions & Classes:**
- Classes: `PascalCase` (e.g., `MarketDataSource`, `PriceCache`, `MarketFeed`)
- Functions: `snake_case` (e.g., `create_source()`, `apply()`)
- Private: Leading underscore (e.g., `_tick()`, `_run()`, `_prices`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `TRADING_SECONDS_PER_YEAR`, `MAX_POLL_INTERVAL`)

**Module & Package Names:**
- Descriptive, singular nouns: `interface`, `cache`, `feed`, `factory`, `stream` (not `interfaces`, `caches`)
- Concrete implementations use the suffix: `simulator.py` (SimulatorSource), `massive.py` (MassiveSource)

## Where to Add New Code

**New API Endpoint (when building FastAPI routes):**
- Primary code: Create a new module in `backend/app/api/` or add handlers to route-specific modules (e.g., `backend/app/api/portfolio.py`, `backend/app/api/chat.py`)
- Tests: `backend/tests/api/test_portfolio.py`, etc.
- Wire into: FastAPI app lifespan and router registration in `main.py` (not yet created)

**New Domain Module (e.g., Portfolio, Chat, Database):**
- Implementation: `backend/app/{domain}/` directory with modules mirroring market data structure
- Example: `backend/app/portfolio/` with `interface.py`, `models.py`, `service.py`, etc.
- Tests: `backend/tests/{domain}/` mirroring package structure
- Public API: Export from `backend/app/{domain}/__init__.py`

**New Utility or Helper:**
- Shared helpers: `backend/app/lib/` or `backend/app/utils/` (if multiple domains use it)
- Domain-specific helpers: Keep within the domain directory (e.g., `backend/app/market/seed_prices.py`)

**Frontend Components (when building):**
- All frontend code: `frontend/` (Next.js project)
- Keep backend and frontend completely separate; no cross-imports
- Frontend talks to backend only via `/api/*` endpoints

**Database Code (when building):**
- Schema and migrations: `backend/app/db/` or `backend/db/` (store schema SQL alongside models)
- ORM models: `backend/app/models/` or keep in domain-specific modules (e.g., `backend/app/portfolio/models.py`)
- Connection/session management: `backend/app/db/session.py` or in lifespan handler

## Special Directories

**`backend/archive/`**
- Purpose: Old implementations, superseded designs
- Generated: No (manually managed)
- Committed: Yes (reference material)
- Content: Earlier iterations of market data, demos, etc.

**`planning/archive/` and `planning/archive_donner/` and `planning/archive_review/`**
- Purpose: Superseded design docs (market data design, reviews, earlier iterations)
- Generated: No (manually managed)
- Committed: Yes (but not referenced; use `planning/MARKET_DATA_SUMMARY.md` instead)
- Content: Detailed design rationale (read only if you need the full derivation)

**`.planning/codebase/`**
- Purpose: Codebase architecture and structure docs for agents
- Generated: Partially (written by gsd-map-codebase agents)
- Committed: Yes (updated as structure evolves)
- Content: ARCHITECTURE.md, STRUCTURE.md (this file), and future CONVENTIONS.md, TESTING.md, etc.

**`backend/tests/__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`**
- Purpose: Build and test artifacts
- Generated: Yes (automatically by pytest, ruff, coverage)
- Committed: No (.gitignore)
- Content: Cached bytecode, test state, lint cache, coverage data

## Future Additions (Planned)

**When building frontend:**
- Create `frontend/` directory with Next.js `package.json`, tsconfig, Tailwind config
- Frontend internal structure: components, pages, lib, styles (up to frontend engineer)

**When building FastAPI app:**
- Create `backend/app/main.py` with lifespan handler, FastAPI() instance, route registration
- Connect market data feed in lifespan setup
- Wire SSE stream router from `app.market.stream`

**When building database layer:**
- Create `backend/app/db/` with schema SQL, connection pooling, transaction management
- Create `backend/app/models/` with SQLAlchemy ORM models or similar
- Create `backend/tests/db/` with database fixture setup (pytest fixture for test database)

**When building portfolio/trading:**
- Create `backend/app/portfolio/models.py` with Position, Trade, Portfolio dataclasses
- Create `backend/app/portfolio/service.py` with trade execution logic, P&L calculation
- Create `backend/app/portfolio/cache.py` or similar for portfolio valuation snapshots
- Create `backend/tests/portfolio/` with full test suite

**When building LLM chat:**
- Create `backend/app/chat/` with message handling, LLM integration, structured output parsing
- Create `backend/app/chat/models.py` with ChatMessage, StructuredResponse dataclasses
- Wire into `/api/chat` endpoint

---

*Structure analysis: 2026-08-12*
