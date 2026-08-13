<!-- GSD:project-start source:PROJECT.md -->

## Project

**FinAlly — AI Trading Workstation**

FinAlly is a Bloomberg-terminal-style AI trading workstation: a single-container web app that streams live simulated market data, lets a user trade a virtual $10,000 portfolio, and includes an AI chat copilot (via OpenRouter/Cerebras) that can analyze the portfolio and execute trades on the user's behalf. It's the capstone project for an agentic AI coding course, built end-to-end by coding agents.

**Core Value:** A user can watch live prices stream, trade a simulated portfolio, and have an AI assistant execute trades and manage the watchlist through natural language — all in one fluid, visually polished terminal-style interface.

### Constraints

- **Tech stack**: Next.js (static export) + FastAPI (Python/uv) + SQLite, single Docker container on port 8000 — fixed by PLAN.md, not open for revisiting
- **Market data source**: Simulator only for this build — no Massive API key available
- **Auth**: None — single hardcoded `user_id="default"` throughout
- **Order types**: Market orders only, instant fill, no fees, no confirmation dialogs
- **LLM provider**: OpenRouter via LiteLLM, Cerebras inference, `gpt-oss-120b`, structured outputs — fixed by PLAN.md
- **Deployment**: Docker only for this build; cloud/Terraform deploy explicitly out of scope

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.12+ - Backend API, market data, portfolio logic
- TypeScript/JavaScript - Frontend (planned, not yet implemented)
- Bash - Start/stop scripts for Docker

## Runtime

- Python 3.12+ (required by `backend/pyproject.toml`)
- Node 20+ (for Next.js build; not yet used)
- uv (Python) - Fast, modern project manager with reproducible lockfile
- npm/pnpm (for Next.js frontend; not yet configured)

## Frameworks

- FastAPI 0.141.1 - REST API framework, SSE streaming, static file serving
- Uvicorn 0.52.1 - ASGI server for FastAPI
- Starlette 1.4.1 - ASGI framework (FastAPI dependency)
- Next.js (static export mode, `output: 'export'`) - Static site generation
- TypeScript - Frontend type safety
- Tailwind CSS - Dark theme styling
- pytest 9.1.1 - Test runner
- pytest-asyncio 1.4.0 - Async test support
- pytest-cov 7.1.0 - Coverage reporting
- ruff 0.16.2 - Fast Python linter and formatter
- python-dotenv 1.2.2 - Environment variable loading from `.env`

## Key Dependencies

- httpx 0.28.1 - Async HTTP client for both Massive API polling and future LLM calls via LiteLLM
- sse-starlette 3.4.8 - Server-Sent Events streaming for `/api/stream/prices`
- pydantic 2.13.4 - Data validation and structured outputs (used for market data models and LLM response parsing)
- uvloop 0.22.1 - High-performance event loop replacement for asyncio
- watchfiles 1.2.0 - File change detection (dev dependency via uvicorn)
- websockets 17.0.1 - WebSocket support (included via uvicorn)
- rich 15.0.0 - Terminal rendering for `market_data_demo.py`
- certifi 2026.7.22 - SSL certificate bundle for HTTPS
- typing-extensions 4.16.0 - Type hint backports for Python 3.12

## Configuration

- `.env` file at project root (gitignored) - Contains API keys and configuration
- Environment variables:
- `backend/pyproject.toml` - Python project metadata, dependencies, and tool configuration
- Ruff config in `pyproject.toml`:
- pytest config in `pyproject.toml`:

## Platform Requirements

- Python 3.12+ (must be installed; system has 3.9.6)
- uv (installed via system package manager or from https://github.com/astral-sh/uv)
- Docker (for containerized deployment)
- Docker container (single image, multi-stage build planned)
- Port: 8000
- SQLite database (self-contained, no external DB server)
- Volume mount: `finally-data:/app/db` for database persistence

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Python modules: `lowercase_with_underscores.py` (e.g., `market_feed.py`, `simulator.py`)
- Test files: `test_*.py` (e.g., `test_simulator.py`, `test_cache.py`)
- Factory files: `factory.py` (e.g., `app/market/factory.py`)
- Snake_case: `create_source()`, `apply()`, `fetch()`, `_advance()`, `_handle_http_error()`
- Private functions/methods: prefixed with `_` (e.g., `_event_multiplier()`, `_format()`, `_extract_price()`)
- Async functions: same convention with `async def` (e.g., `async def fetch()`)
- Snake_case: `poll_interval`, `market_shock`, `cache_key`, `_rng`
- Instance attributes: prefixed with `_` when private (e.g., `self._prices`, `self._source`)
- Loop variables: descriptive where possible (e.g., `for update in cache.snapshot()`)
- PascalCase for classes: `MarketDataSource`, `SimulatorSource`, `PriceCache`, `Quote`, `PriceUpdate`
- Abstract base classes: `MarketDataSource` (interface), concrete implementations: `SimulatorSource`, `MassiveSource`
- Dataclasses: frozen immutable types (e.g., `Quote`, `PriceUpdate`, `TickerProfile`)
- UPPER_CASE: `TRADING_SECONDS_PER_YEAR`, `TICK_SECONDS`, `MAX_POLL_INTERVAL`, `FALLBACK_STATUS_CODES`
- Module-level constants grouped near top of file, before class definitions

## Code Style

- Line length: 100 characters (ruff configured, E501 ignored)
- Target Python version: 3.12
- No formatter enforced (black/autopep8 not in dependencies); style via linting only
- Tool: ruff (`ruff>=0.7.0`)
- Rules enabled: E (pycodestyle errors), F (Pyflakes), I (isort), N (pep8-naming), W (pycodestyle warnings)
- Configuration in `pyproject.toml`: `[tool.ruff]` and `[tool.ruff.lint]`
- Example: `ruff check app/ tests/`

## Type Hints

- Type hints required on all function signatures and method definitions
- Return types always specified: `-> list[Quote]`, `-> None`, `-> float | None`
- Union types use modern syntax: `str | None`, `dict[str, float]`, not `Optional[T]` or `Union[T, U]`
- Async iterators typed: `AsyncIterator[dict]`

## Import Organization

- Relative imports within same package: `from .cache import PriceCache`
- Absolute imports from app root: `from app.market import Quote`
- No package-level `__init__` imports except in `__all__` exports

## Docstrings

- One-liner describing the module's purpose at the top: `"""The unified market data source contract."""`
- Can include architectural notes for complex modules
- Multi-line for non-trivial classes
- Include a "Contract" section for abstract base classes or classes with special invariants
- Document thread safety if relevant (e.g., `PriceCache` notes single-writer model)
- One-liner for simple functions: `"""Release any held resources. Overridden where needed."""`
- Multi-line for complex logic or side effects
- Use active voice, imperative mood: "Advance every requested ticker one tick" not "Advances..."
- Document field purpose as docstring under field definition:
- Sparingly used; explain *why*, not *what*
- Example: `# hashlib not hash() — Python salts hash() for strings with per-process seed`
- Example: `# log space to guarantee positivity in GBM`

## Error Handling

- `logger.exception(msg)` — logs stack trace at ERROR level
- `logger.warning(msg)` — for degraded but recoverable conditions
- Include context: `logger.error("market source %r rejected (HTTP %s)", name, status)`
- Use `.get()` with sensible defaults: `self._prices.get(ticker, profile.anchor)`
- Early returns for edge cases: `if not tickers: return []`
- Fall-through chains for graceful degradation (e.g., `_extract_price` in `app/market/massive.py`)
- Don't catch exceptions you don't understand
- Don't add null checks where contracts guarantee non-null
- Example: `PriceCache.apply()` doesn't check if quote is None because `Quote` is required parameter

## Data Models

- Use `frozen=True` for immutable data (required for hashability, safety):
- Use `slots=True` for memory efficiency
- All dataclass fields should have type hints
- Computed fields implemented as `@property` for cleaner API:

## Async/Await Patterns

- Always mark with `async def`: `async def fetch(self, tickers: Sequence[str])`
- Use `await` for async operations: `await self._source.fetch(...)`
- Async context managers for cleanup: `async with ... as ...:` (not yet used, but pattern for resources)
- Used for streaming: `async def price_events(cache) -> AsyncIterator[dict]:`
- Yield dicts/events, not structured objects for JSON compatibility
- Cleanup with `await gen.aclose()` or catch `asyncio.CancelledError`
- Created with `asyncio.create_task(coro)` (not `asyncio.ensure_future`)
- Cleanup: check if task is done with `task.done()`, cancel with `task.cancel()`, await to consume the `CancelledError`

## Dependency Injection

- Constructor injection (pass dependencies to `__init__`)
- Optional dependencies with defaults: `client: httpx.AsyncClient | None = None`
- Factory functions that encapsulate env-based selection: `create_source()` returns either `MassiveSource` or `SimulatorSource`

## Module Exports

- Explicitly define what is exported from a module
- Example from `app/market/__init__.py`:

## Determinism & Testing

- Use `hashlib` instead of built-in `hash()` for stable string→number mapping
- Respect `MARKET_SEED` environment variable for simulator reproducibility
- Example: `profile_for(ticker)` uses `hashlib.md5()` to generate deterministic prices for unknown tickers

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| MarketDataSource (interface) | Abstract contract for fetching quotes | `backend/app/market/interface.py` |
| SimulatorSource | Geometric Brownian motion price generation | `backend/app/market/simulator.py` |
| MassiveSource | REST client for Massive snapshot endpoint | `backend/app/market/massive.py` |
| MarketFeed | Background polling task with resilience logic | `backend/app/market/feed.py` |
| PriceCache | In-memory latest/previous price store | `backend/app/market/cache.py` |
| PriceUpdate | Quote + previous price + derived direction | `backend/app/market/models.py` |
| Quote | Raw price observation from a source | `backend/app/market/models.py` |
| create_source() | Environment-aware factory seam | `backend/app/market/factory.py` |
| create_stream_router() | SSE streaming endpoint factory | `backend/app/market/stream.py` |

## Pattern Overview

- **Abstract interface pattern**: `MarketDataSource` ABC allows swapping simulator and Massive without changing downstream code
- **Factory pattern**: `create_source()` is the single seam where environment variables determine behavior
- **Cache-based architecture**: Read-once-from-cache pattern means the two sources cannot disagree about price direction
- **Resilient background tasks**: `MarketFeed` gracefully handles network failures, auth rejection, and rate limiting
- **Frozen dataclasses**: `Quote` and `PriceUpdate` are immutable, supporting safe concurrent reads
- **Decoupled timing**: Sources poll at different rates (simulator 500ms, Massive 15s), but cache and SSE operate independently

## Layers

- Purpose: Fetch current prices for a list of tickers
- Location: `backend/app/market/simulator.py`, `backend/app/market/massive.py`
- Contains: `SimulatorSource` (GBM with Ornstein-Uhlenbeck anchor pull), `MassiveSource` (async httpx REST client)
- Depends on: `Quote` model, `MarketDataSource` interface
- Used by: `MarketFeed`
- Purpose: Poll a source on a configurable interval and write into cache; handle failures gracefully
- Location: `backend/app/market/feed.py`
- Contains: `MarketFeed` task lifecycle (start/stop), polling loop, error handling and recovery logic
- Depends on: `MarketDataSource`, `PriceCache`
- Used by: FastAPI lifespan handler (not yet implemented)
- Purpose: Store the latest and previous price per ticker; sole owner of direction computation
- Location: `backend/app/market/cache.py`
- Contains: `PriceCache.apply()` (write quotes, return changed updates), `get()` (read latest), `snapshot()` (read all)
- Depends on: `Quote`, `PriceUpdate` models
- Used by: SSE streaming, portfolio valuation (when implemented), frontend (via SSE)
- Purpose: Expose prices to the frontend via server-sent events
- Location: `backend/app/market/stream.py`
- Contains: `create_stream_router(cache)` factory, `price_events()` async generator, event formatting
- Depends on: `PriceCache`, FastAPI
- Used by: FastAPI app (not yet wired)

## Data Flow

### Primary Request Path (Market Data)

### Error Recovery Path

- **Source state**: Held by `MarketFeed._source`; sources are stateless (each fetch is independent)
- **Cache state**: `PriceCache._prices` dict (ticker → latest PriceUpdate); no external persistence yet
- **Feed state**: `MarketFeed._task` (background task handle), `_base_interval` and `poll_interval` (for backoff tracking)
- **No global state**: Everything is passed as dependencies; no module-level singletons in market package

## Key Abstractions

- Purpose: Contract for fetching current quotes; shields downstream code from which source is active
- Examples: `SimulatorSource` (`backend/app/market/simulator.py`), `MassiveSource` (`backend/app/market/massive.py`)
- Pattern: Abstract base class with one abstract method `fetch(tickers) -> list[Quote]`
- Purpose: Quote paired with previous price; sole owner of direction ("up", "down", "flat")
- Examples: Returned by `PriceCache.apply()`, sent via SSE
- Pattern: Frozen dataclass with derived properties (`change`, `change_percent`, `direction`)
- Purpose: Lifecycle management and resilient polling of a data source
- Examples: One instance per FastAPI app (not yet wired)
- Pattern: Background task with start/stop lifecycle, error handling escalation (transient → fallback → backoff)

## Entry Points

- Location: `backend/app/market/factory.py`
- Triggers: Must be called during FastAPI app initialization (lifespan handler)
- Responsibilities: Read `MASSIVE_API_KEY` environment variable; return `SimulatorSource` or `MassiveSource`
- Location: `backend/app/market/stream.py:create_stream_router()`
- Triggers: GET request with no parameters
- Responsibilities: Return SSE stream of price updates; send snapshot on connect, then changes only; heartbeat every 15s

## Architectural Constraints

- **Single-threaded via asyncio**: No locks in `PriceCache` — only one `MarketFeed._run()` task writes to cache, all readers are safe
- **No persistence**: `PriceCache` is in-memory; prices lost on app restart until a trade history snapshot system is built
- **No multi-user state yet**: All code defaults to single `user_id="default"` (not used in market data layer yet)
- **Environment-determined behavior**: `MASSIVE_API_KEY` must be set before app starts; cannot switch sources at runtime
- **Resilience boundary**: `MarketFeed` absorbs all upstream failures; downstream code sees only stale-but-valid cache

## Anti-Patterns

### Directly calling a source's `fetch()` from business logic

- Defeats the source abstraction — code now knows which source is active
- Causes duplicate polling if business logic also reads the cache
- Prevents future multi-source scenarios (e.g., real-time + fallback)

### Synchronously calling Massive client from FastAPI

### Calling `MarketFeed.start()` more than once

## Error Handling

- Transient errors (connection timeout, 500, 503): Log at ERROR level, continue serving cached prices
- Auth/plan failure (401, 403): Log at ERROR, swap to `fallback_factory()` one time
- Rate limiting (429): Log at WARNING, increase poll interval up to 60s, continue polling
- Structurally invalid response (JSON parse error, missing fields): Treated as transient, not fatal

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| cerebras-inference | Use this to write code to call an LLM using LiteLLM and OpenRouter with the Cerebras inference provider | `.claude/skills/cerebras/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
