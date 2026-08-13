<!-- refreshed: 2026-08-12 -->
# Architecture

**Analysis Date:** 2026-08-12

## System Overview

Currently, the FinAlly platform has a **backend-only implementation** with a complete market data subsystem. The frontend, FastAPI app integration, database layer, and portfolio/trading logic are planned but not yet implemented. The following diagram represents the completed market data layer:

```text
┌─────────────────────────────────────────────────────────────┐
│                  Market Data Sources                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Environment Variable (MASSIVE_API_KEY)              │   │
│  │           ▼                     ▼                     │   │
│  │    SimulatorSource       MassiveSource                │   │
│  │    (GBM, local)          (REST polling)              │   │
│  └──────────────────────────────────────────────────────┘   │
│           ▲                          ▲                       │
└───────────┼──────────────────────────┼───────────────────────┘
            │                          │
            │                          │
┌───────────┴──────────────────────────┴───────────────────────┐
│                 Abstract Interface                            │
│              MarketDataSource (fetch)                        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Background Feed Task                            │
│         MarketFeed (polling loop)                           │
│  `backend/app/market/feed.py`                              │
│  - Configurable poll interval                              │
│  - Resilience: log & continue on transient errors          │
│  - Fallback: 401/403 → SimulatorSource                     │
│  - Backoff: 429 → exponential backoff                      │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            In-Memory Price Cache                             │
│            PriceCache (read-only)                           │
│  `backend/app/market/cache.py`                             │
│  - Latest/previous price per ticker                        │
│  - Sole owner of direction computation                     │
│  - No locks: single-threaded via asyncio                   │
└────────────────────────┬──────────┬──────────────────────────┘
                         │          │
               ┌─────────┘          └──────────┐
               │                               │
               ▼                               ▼
        ┌────────────────┐          ┌────────────────────┐
        │  SSE Streaming  │          │ Portfolio Logic    │
        │  (not yet)      │          │ (not yet)          │
        │ /api/stream/... │          │                    │
        └────────────────┘          └────────────────────┘
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

**Overall:** Multi-layered interface-driven architecture with environment-determined concrete implementations.

**Key Characteristics:**
- **Abstract interface pattern**: `MarketDataSource` ABC allows swapping simulator and Massive without changing downstream code
- **Factory pattern**: `create_source()` is the single seam where environment variables determine behavior
- **Cache-based architecture**: Read-once-from-cache pattern means the two sources cannot disagree about price direction
- **Resilient background tasks**: `MarketFeed` gracefully handles network failures, auth rejection, and rate limiting
- **Frozen dataclasses**: `Quote` and `PriceUpdate` are immutable, supporting safe concurrent reads
- **Decoupled timing**: Sources poll at different rates (simulator 500ms, Massive 15s), but cache and SSE operate independently

## Layers

**Source Layer:**
- Purpose: Fetch current prices for a list of tickers
- Location: `backend/app/market/simulator.py`, `backend/app/market/massive.py`
- Contains: `SimulatorSource` (GBM with Ornstein-Uhlenbeck anchor pull), `MassiveSource` (async httpx REST client)
- Depends on: `Quote` model, `MarketDataSource` interface
- Used by: `MarketFeed`

**Feed Layer:**
- Purpose: Poll a source on a configurable interval and write into cache; handle failures gracefully
- Location: `backend/app/market/feed.py`
- Contains: `MarketFeed` task lifecycle (start/stop), polling loop, error handling and recovery logic
- Depends on: `MarketDataSource`, `PriceCache`
- Used by: FastAPI lifespan handler (not yet implemented)

**Cache Layer:**
- Purpose: Store the latest and previous price per ticker; sole owner of direction computation
- Location: `backend/app/market/cache.py`
- Contains: `PriceCache.apply()` (write quotes, return changed updates), `get()` (read latest), `snapshot()` (read all)
- Depends on: `Quote`, `PriceUpdate` models
- Used by: SSE streaming, portfolio valuation (when implemented), frontend (via SSE)

**Streaming Layer:**
- Purpose: Expose prices to the frontend via server-sent events
- Location: `backend/app/market/stream.py`
- Contains: `create_stream_router(cache)` factory, `price_events()` async generator, event formatting
- Depends on: `PriceCache`, FastAPI
- Used by: FastAPI app (not yet wired)

## Data Flow

### Primary Request Path (Market Data)

1. **Initialization** — Not yet called: FastAPI lifespan handler will call `MarketFeed.start()` with `create_source()` and `PriceCache`
2. **Background polling** — `MarketFeed._run()` loop calls `_source.fetch(watchlist_tickers)` every `poll_interval` seconds
3. **Cache application** — Quotes written to `PriceCache.apply()`, which returns only tickers with changed prices
4. **SSE dispatch** — `price_events()` generator polls `cache.snapshot()` every 500ms and yields JSON-formatted updates
5. **Client reception** — Frontend receives SSE events via `EventSource` API, updates UI with price flashes

### Error Recovery Path

1. **Transient failure** (RuntimeError, timeout, etc.) → Logged, loop continues serving stale cache
2. **HTTP 401/403** (auth failed) → One-time swap to `fallback_factory()` (typically SimulatorSource)
3. **HTTP 429** (rate limited) → Double poll interval (exponential backoff, capped at 60s), retry on next tick
4. **Successful recovery** → Reset poll interval to base interval on next successful fetch

**State Management:**
- **Source state**: Held by `MarketFeed._source`; sources are stateless (each fetch is independent)
- **Cache state**: `PriceCache._prices` dict (ticker → latest PriceUpdate); no external persistence yet
- **Feed state**: `MarketFeed._task` (background task handle), `_base_interval` and `poll_interval` (for backoff tracking)
- **No global state**: Everything is passed as dependencies; no module-level singletons in market package

## Key Abstractions

**MarketDataSource:**
- Purpose: Contract for fetching current quotes; shields downstream code from which source is active
- Examples: `SimulatorSource` (`backend/app/market/simulator.py`), `MassiveSource` (`backend/app/market/massive.py`)
- Pattern: Abstract base class with one abstract method `fetch(tickers) -> list[Quote]`

**PriceUpdate:**
- Purpose: Quote paired with previous price; sole owner of direction ("up", "down", "flat")
- Examples: Returned by `PriceCache.apply()`, sent via SSE
- Pattern: Frozen dataclass with derived properties (`change`, `change_percent`, `direction`)

**MarketFeed:**
- Purpose: Lifecycle management and resilient polling of a data source
- Examples: One instance per FastAPI app (not yet wired)
- Pattern: Background task with start/stop lifecycle, error handling escalation (transient → fallback → backoff)

## Entry Points

**`create_source()`:**
- Location: `backend/app/market/factory.py`
- Triggers: Must be called during FastAPI app initialization (lifespan handler)
- Responsibilities: Read `MASSIVE_API_KEY` environment variable; return `SimulatorSource` or `MassiveSource`

**`/api/stream/prices` (not yet wired):**
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

**What happens:** Portfolio valuation or trade execution code calls `SimulatorSource.fetch()` or `MassiveSource.fetch()` directly to get prices.

**Why it's wrong:** 
- Defeats the source abstraction — code now knows which source is active
- Causes duplicate polling if business logic also reads the cache
- Prevents future multi-source scenarios (e.g., real-time + fallback)

**Do this instead:** Always read from `PriceCache.get(ticker)` or `cache.snapshot()`. The cache is populated by `MarketFeed`, which is the single authoritative reader of the source. See example in `planning/MARKET_DATA_SUMMARY.md` §Usage.

### Synchronously calling Massive client from FastAPI

**What happens:** Code imports the official `polygon.io` (Massive) Python client and calls its synchronous methods in a FastAPI route handler.

**Why it's wrong:** Synchronous network I/O blocks the asyncio event loop, starving other concurrent connections (e.g., stalled SSE clients).

**Do this instead:** Use the async `httpx.AsyncClient` as `MassiveSource` does. See `backend/app/market/massive.py` for the pattern.

### Calling `MarketFeed.start()` more than once

**What happens:** App startup handler calls `feed.start()` twice without stopping, leaking the first background task.

**Why it's wrong:** Two polling loops write to the same cache concurrently, which invalidates the lock-free guarantee.

**Do this instead:** Call `feed.start()` exactly once during lifespan setup, and `await feed.stop()` during lifespan cleanup. `start()` raises `RuntimeError` if already running. See example in `planning/MARKET_DATA_SUMMARY.md` §Usage.

## Error Handling

**Strategy:** Fail soft on transient errors; fail hard only on permanent auth/configuration failures.

**Patterns:**
- Transient errors (connection timeout, 500, 503): Log at ERROR level, continue serving cached prices
- Auth/plan failure (401, 403): Log at ERROR, swap to `fallback_factory()` one time
- Rate limiting (429): Log at WARNING, increase poll interval up to 60s, continue polling
- Structurally invalid response (JSON parse error, missing fields): Treated as transient, not fatal

## Cross-Cutting Concerns

**Logging:** `app/market/` uses Python's standard `logging` module. `MarketFeed._run()` logs fetch failures, auth fallbacks, and backoff events. Tests clean up environment variables via `conftest.py` autouse fixture.

**Validation:** Minimal — sources return what the API gives them. `PriceCache.apply()` accepts any Quote and computes direction; no price validation (negative prices, NaN, etc. are structurally impossible in the GBM simulator, and Massive responses are trusted).

**Error propagation:** `MarketFeed._tick()` catches all exceptions except `asyncio.CancelledError` (which is re-raised to stop the loop cleanly). Errors are logged but do not propagate to the FastAPI lifespan handler — the feed is designed to be independent of app health.

---

*Architecture analysis: 2026-08-12*
