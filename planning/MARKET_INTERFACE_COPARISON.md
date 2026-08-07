# Market Interface Comparison

Compared:

- Current: `planning/MARKET_INTERFACE.md`
- Archived: `planning/archive/MARKET_INTERFACE.md`

## Fundamental Differences

- **Architecture changed from push to pull.** The archived design makes each data source own its polling task and push updates into a shared cache. The current design reduces the source contract to `fetch(tickers)` and introduces a separate `MarketFeed` that owns polling, timing, cache writes, and error containment.
- **The interface is much smaller.** The archived `MarketDataSource` exposes `start`, `stop`, ticker mutation, and ticker inspection methods. The current interface exposes only `fetch`, optional cleanup through `aclose`, and a source-defined `poll_interval`.
- **Ticker ownership moved out of data sources.** The archived implementations maintain their own mutable ticker lists. The current feed receives a callable that reads the latest watchlist, so additions and removals are discovered automatically on the next poll without coupling market sources to database or watchlist logic.
- **The data model was split by responsibility.** The archive has only `PriceUpdate`, including stored `change` and `direction` values and a Unix timestamp. The current design adds an immutable `Quote` for raw source observations, makes `PriceUpdate` immutable, uses timezone-aware `datetime` values, and derives `change`, `change_percent`, and `direction` through properties.
- **Previous-price logic is centralized.** In the current design, sources report only current observations and `PriceCache` alone determines the previous price and direction. This prevents the simulator and Massive implementation from independently producing inconsistent movement data.
- **Cache concurrency assumptions changed.** The archived cache uses a thread lock because source implementations write independently. The current cache has no lock because one asyncio feed task is the sole writer and cache operations contain no `await`.
- **Cache output behavior changed.** The archive returns all cached values through `get_all()` and supports explicit removal. The current cache exposes `snapshot()`, returns only new or price-changing updates from `apply()`, and intentionally keeps ephemeral data only for the process lifetime.
- **Massive integration changed libraries.** The archived design uses the synchronous official `massive` client through `asyncio.to_thread`. The current design uses `httpx.AsyncClient` directly against the snapshot endpoint to avoid blocking the FastAPI event loop and unnecessary client-library complexity.
- **Massive price extraction is more defensive.** The current design defines a fallback order of `lastTrade.p`, minute close, day close, then previous-day close, covering zeroed intraday snapshot fields outside market hours. The archive assumes `last_trade.price` is always usable.
- **Simulator responsibility was reduced.** The archive describes a simulator that owns its run loop, ticker mutations, and cache writes. The current simulator advances one step per `fetch`, always supplies requested symbols, and leaves scheduling and caching to `MarketFeed`.
- **Source selection is more isolated.** The archive factory accepts and injects a cache into concrete sources. The current `create_source()` has no cache dependency and is the only environment-aware seam, selecting Massive for a nonblank `MASSIVE_API_KEY` and otherwise selecting the simulator.
- **Configuration expanded.** The current document adds `MARKET_POLL_INTERVAL` for Massive and `MARKET_SEED` for deterministic simulator runs, while explicitly treating unset, empty, and whitespace-only API keys as absent.
- **Failure handling is now specified.** The archive does not define an upstream failure policy. The current design retains stale cache data on transient errors, proposes retry/backoff for rate limits and network/server failures, and specifies simulator fallback for permanent authentication or subscription failures.
- **SSE behavior became incremental.** The archive sends the complete ticker map every 500 ms. The current design sends a full snapshot when a subscriber connects, then only changed tickers, while keeping SSE cadence independent from source polling cadence and using heartbeat comments for idle connections.
- **FastAPI lifecycle wiring is explicit.** The current design shows one source, feed, and cache created for the application lifespan and stored through app state. The archive describes lifecycle steps but leaves orchestration distributed across source methods and callers.
- **Module boundaries are clearer.** The archive combines models and cache concepts in `interface.py` and names the live provider `massive_client.py`. The current design assigns separate modules for models, interface, cache, feed, factory, simulator, and Massive implementation, with an explicit one-way dependency graph.
- **Public API exposure is constrained.** The current package exports abstractions and orchestration helpers but intentionally does not export concrete source classes, encouraging application code to use `create_source()` and depend on the interface.
- **Testing guidance is substantially stronger.** The current document defines coverage for contract conformance, cache semantics, payload parsing, HTTP failures, feed resilience, factory selection, deterministic simulation, and a strict no-network test policy. The archive contains no equivalent verification plan.

## Developer Impact

- Existing code written against archived methods such as `source.start()`, `add_ticker()`, `remove_ticker()`, or `get_tickers()` must be migrated to `MarketFeed` plus a live ticker-provider callable.
- Consumers must handle `datetime` timestamps instead of Unix-second floats and should treat `change`, `change_percent`, and `direction` as computed properties rather than stored constructor fields.
- SSE clients must accept individual changed-ticker events after the initial snapshot instead of expecting a complete ticker dictionary every 500 ms.
- Tests and mocks should implement `fetch()` and `aclose()` rather than simulating source-owned background loops.
- The current document is roughly twice as detailed and should be treated as the authoritative architecture; the archived file is an earlier implementation sketch with materially different contracts.

## Notable Specification Gap

- The current document specifies automatic Massive-to-simulator fallback for HTTP 401/403 and exponential backoff for HTTP 429, but the shown `MarketFeed` and factory code only log generic exceptions and retry at the unchanged interval. Implementation must add explicit status-aware switching/backoff logic for the documented failure policy to be fully realized.
