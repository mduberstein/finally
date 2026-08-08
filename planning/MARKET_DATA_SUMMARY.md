# Market Data Backend — Implementation Summary

Status: **complete**. This summarizes the current state of `backend/app/market/`
for downstream agents (portfolio, SSE wiring, frontend) so they don't need to
re-read the full design doc. For derivations, verification evidence, and the
complete rationale behind each decision, see `planning/MARKET_DATA_DESIGN.md`
(the authoritative build reference) and `planning/MARKET_DATA_REVIEW.md` (the
code review and its fixes). `planning/archive/` holds superseded drafts — do
not use it as a reference.

## Architecture

Live prices are sourced from either a built-in simulator or the Massive
(Polygon.io) REST API, selected once by an environment variable, and exposed
through a single abstract interface so nothing downstream needs to know or
care which is active:

- No `MASSIVE_API_KEY` → `SimulatorSource` generates believable, correlated,
  always-positive prices via geometric Brownian motion at 2 Hz. No network,
  no external dependency — the default and the primary demo experience.
- `MASSIVE_API_KEY` set → `MassiveSource` polls the Massive REST snapshot
  endpoint, default every 15s (`MARKET_POLL_INTERVAL`).

Both implement `MarketDataSource.fetch(tickers) -> list[Quote]`. A background
`MarketFeed` task polls whichever source is active and writes into a
`PriceCache`, which is the only component that remembers a previous price and
derives direction — so the two sources can never disagree about "did it go
up." Source poll cadence is decoupled from stream cadence: the simulator ticks
every 500ms and Massive polls every 15s, but both look identical to a reader
of the cache.

```
factory ──> simulator ──┐
        └─> massive ────┴──> interface ──> models
                                              ^
feed ──> cache ───────────────────────────────┘
```

`cache.py` and `feed.py` never import a concrete source; `simulator.py` and
`massive.py` never import each other. Application code depends only on
`MarketDataSource`, obtained via `create_source()` — concrete source classes
are intentionally not exported from the package (see Usage section below).

Upstream failures degrade gracefully rather than crashing the app: a
transient error is logged and the loop continues serving stale cached prices;
an HTTP 401/403 (permanent auth/plan failure) triggers a one-time fallback to
a caller-supplied `fallback_factory`; an HTTP 429 doubles the poll interval
up to a 60s ceiling.

## Modules

All under `backend/app/market/`:

| Module | Responsibility |
|---|---|
| `models.py` | `Quote` (a raw price observation) and `PriceUpdate` (a quote paired with its previous price, with `change`/`change_percent`/`direction` derived properties) — both frozen dataclasses |
| `interface.py` | `MarketDataSource` ABC — one abstract method, `fetch(tickers) -> list[Quote]`, plus an optional `aclose()` |
| `simulator.py` | `SimulatorSource` — the GBM simulator (see Key Design Decisions) |
| `seed_prices.py` | Per-ticker `TickerProfile` (anchor price, volatility, correlation beta) for the 10 default tickers, plus a deterministic synthetic profile for any unknown ticker |
| `massive.py` | `MassiveSource` — REST client for the Massive snapshot endpoint |
| `cache.py` | `PriceCache` — in-memory latest/previous price store; the sole owner of direction |
| `feed.py` | `MarketFeed` — background polling task with 401/403 fallback and 429 backoff |
| `factory.py` | `create_source()` — the one environment-aware seam that picks simulator vs. Massive |
| `stream.py` | `create_stream_router(cache)` — builds the `/api/stream/prices` SSE endpoint |
| `__init__.py` | Public exports: `MarketDataSource`, `MarketFeed`, `PriceCache`, `PriceUpdate`, `Quote`, `create_source` |

## Key Design Decisions

- **One seam for environment branching.** `create_source()` is the only place
  in the package that reads `MASSIVE_API_KEY`. Everything else — cache, feed,
  stream, and any future caller — depends only on the abstract
  `MarketDataSource` type.
- **Pull, not push.** A source just answers "what is the price now" via
  `fetch()`; a separate `MarketFeed` owns timing. No callbacks or observer
  registration.
- **Cache owns direction, not the sources.** `Quote` has no `previous_price`
  field; only `PriceCache.apply()` can produce a `PriceUpdate` with a
  `direction`. This makes it structurally impossible for the two sources to
  disagree about whether a price went up.
- **GBM simulator, anchor-pulled, not clamped.** Prices follow geometric
  Brownian motion pulled back toward a per-ticker anchor in log space
  (Ornstein-Uhlenbeck), so they wander realistically without drifting to
  absurd long-run values, and are correlated across tickers via one shared
  `market_shock` draw per tick scaled by a per-ticker `beta` (tech tickers
  have higher beta and move together more than cross-sector pairs).
  Positivity is guaranteed by the `exp(...)` structure itself — there is no
  `max(price, ...)` clamp anywhere. Rare 2-5% "drama events"
  (`EVENT_PROBABILITY = 8e-5` per tick) add demo excitement without swamping
  the statistics (events are disabled in tests that measure volatility/
  correlation, since a single jump dwarfs normal diffusion).
- **`hashlib.md5`, not the built-in `hash()`, for unknown tickers.** Python
  salts `hash()` per-process unless `PYTHONHASHSEED` is fixed, which would
  give an unrecognized ticker a different price after every restart.
  `hashlib.md5` is stable across processes and machines; it's used purely as
  a string→number map, not as a security primitive.
- **Massive uses raw `httpx`, not the official client.** The official
  `massive`/Polygon client is synchronous (built on `urllib3`); calling it
  from a FastAPI coroutine would block the event loop and stall every open
  SSE connection.
- **Massive's price fallback ladder.** `lastTrade → min → day → prevDay`,
  because snapshot bars are zeroed nightly at 3:30 AM ET and repopulate from
  4:00 AM — falling through to `prevDay.c` (always populated) avoids
  reporting a bogus `$0.00` quote outside trading hours.
- **`MarketFeed` fails soft, with two specific escalations.** Any exception
  during a tick is logged and the loop continues on stale cache data. HTTP
  401/403 is treated as permanent (wrong key/plan) and triggers a one-time
  swap to `fallback_factory()`, typically `SimulatorSource`. HTTP 429 doubles
  `poll_interval` up to `MAX_POLL_INTERVAL = 60.0`, then resets to the base
  interval on the next successful fetch.
- **SSE payload is explicitly JSON-encoded**, not left as a nested dict —
  `sse_starlette` falls back to `str(data)` for non-string payloads, which
  produces a Python repr (single-quoted) that `JSON.parse` on the frontend
  cannot read. A regression test guards this.
- **SSE heartbeat comes from the library default, not custom code.**
  `sse_starlette.EventSourceResponse` defaults `ping_interval` to 15s and
  sends a `: ping` comment automatically, satisfying the design doc's
  "keep idle connections and intermediate proxies alive" requirement without
  extra code (confirmed by reading the installed library source; documented
  in `stream.py` with a one-line comment so it isn't "fixed" redundantly).

## Test Suite

`backend/tests/market/` — **101 tests pass**, **99% statement coverage**:

```
Name                        Stmts   Miss  Cover   Missing
---------------------------------------------------------
app/market/__init__.py          6      0   100%
app/market/cache.py            19      0   100%
app/market/factory.py          14      0   100%
app/market/feed.py             62      1    98%   84
app/market/interface.py        10      0   100%
app/market/massive.py          24      0   100%
app/market/models.py           28      0   100%
app/market/seed_prices.py      19      0   100%
app/market/simulator.py        45      0   100%
app/market/stream.py           28      1    96%   63
---------------------------------------------------------
TOTAL                         255      2    99%
```

The two remaining uncovered lines are both defensive/framework code not worth
contriving a test for: `feed.py`'s `except asyncio.CancelledError: raise`
inside `_tick()` (cancellation in practice always lands inside `_run`'s
`asyncio.sleep`), and the thin FastAPI route body in `stream.py` (the actual
logic lives in the separately-tested `price_events` generator).

Test files, one per module plus fixtures:

| File | Covers |
|---|---|
| `test_models.py` | `Quote`/`PriceUpdate`, `change`/`change_percent`/`direction` derivation, division-by-zero edge case |
| `test_interface.py` | `MarketDataSource` contract, parametrized across both concrete sources |
| `test_cache.py` | First-sighting is `flat`, rise/fall direction, unchanged price not reported as changed |
| `test_simulator.py` | Determinism (seeded runs produce identical price sequences), positivity over 2000 ticks, GBM statistics (volatility/correlation with events disabled), and `TestSimulatorSourceEvents` — direct tests of the drama-event jump branch (magnitude bounds, up/down direction) |
| `test_seed_prices.py` | Known-ticker profiles, deterministic synthetic profile for unknown tickers |
| `test_massive.py` | Snapshot parsing, the `lastTrade → min → day → prevDay` fallback ladder, zero-value edge case, HTTP error handling — all via `httpx.MockTransport`, no network |
| `test_factory.py` | Unset/empty/whitespace `MASSIVE_API_KEY` selects the simulator; a real key selects Massive; poll interval parsing including an invalid value falling back to the 15.0 default |
| `test_feed.py` | Resilience to transient failures, 401/403 fallback, 429 backoff and reset, and `MarketFeed.start()` idempotency (`test_start_twice_raises`, `test_start_after_stop_is_allowed`) |
| `test_stream.py` | SSE frame shape, JSON (not repr) encoding, snapshot-then-changes-only behavior |
| `conftest.py` | Shared fixtures |

Run with:
```bash
cd backend
uv run pytest -v --cov=app --cov-report=term-missing
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/
```

## Code Review and Fixes Applied

A full code review (`planning/MARKET_DATA_REVIEW.md`) was carried out against
the design docs, and every actionable finding was fixed in a follow-up pass:

- **Lint**: removed an unused `UTC` import in `test_massive.py`.
- **Format**: ran `ruff format` across the modules that had drifted.
- **Drama-event coverage gap closed**: added `TestSimulatorSourceEvents`,
  four tests that directly drive `_event_multiplier`'s jump branch instead of
  relying on disabled-event statistics tests to imply it's correct.
- **`MARKET_POLL_INTERVAL` validation gap closed**: added a test for an
  invalid value falling back to the 15.0 default.
- **`MarketFeed.start()` made idempotent-safe**: it now raises `RuntimeError`
  if called while already running, rather than silently leaking the previous
  background task (it would otherwise keep polling and writing into the
  cache alongside the new one).
- **`stream.py` heartbeat documented**: a one-line comment explains the
  15s ping is handled by `sse_starlette`'s default, so a future reader
  doesn't "helpfully" add a redundant one.

Result: went from 94 to **101 tests**, 98% to **99% coverage**, zero
`ruff check`/`ruff format` findings. Both commits (`Apply fixes from market
data backend review`, plus a small bot follow-up moving `rich` to an optional
dependency — see Demo section) are merged into `main`.

One item was deliberately **not** fixed, because it isn't a defect in this
module: the `fallback_factory` wiring is inert until something constructs a
`MarketFeed(..., fallback_factory=SimulatorSource)` — that belongs in the
FastAPI `lifespan` handler described in Usage below, which doesn't exist yet.

## Demo

`backend/market_data_demo.py` is a standalone CLI proof that the simulator
works, using `SimulatorSource`, `PriceCache`, and `seed_prices.PROFILES`
directly — no FastAPI, no network. It renders a live Rich dashboard for all
10 default tickers: price, $ and % change, a color-coded direction arrow
(▲/▼/►, driven by `PriceUpdate.direction`), a rolling 30-tick unicode
sparkline, and an "Event Log" panel logging any single-tick move ≥1%. It runs
for 60 seconds or until Ctrl+C.

`rich` is intentionally an optional `demo` extra in `pyproject.toml` (not a
core dependency of the FastAPI app), and `EVENT_PROBABILITY` is locally
raised ~4x for the duration of the demo process only, so a 60s run reliably
shows a handful of drama events in the log instead of the ~1 expected at the
production rate — this doesn't change how a jump itself is computed.

Run it with:
```bash
cd backend
uv sync --extra demo
uv run --extra demo market_data_demo.py
```

## Usage in Downstream Code

Nothing outside `app/market/` consumes this yet — there is no FastAPI app,
`lifespan` handler, or route wiring in the repository. `planning/
MARKET_DATA_DESIGN.md` §10 specifies the intended integration; whoever builds
the FastAPI app should follow it:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import MarketFeed, PriceCache, create_source
from app.market.simulator import SimulatorSource

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = PriceCache()
    feed = MarketFeed(
        create_source(), cache, watchlist_tickers,
        fallback_factory=SimulatorSource,  # remember to pass this explicitly
    )
    feed.start()
    app.state.prices = cache
    yield
    await feed.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(create_stream_router(cache))
```

Notes for whoever writes this:

- **One feed, one cache, for the process lifetime.** `watchlist_tickers` is a
  callable supplied by the portfolio/watchlist module that reads the current
  watchlist (from SQLite or an in-memory copy of it) — the market package
  never queries the database directly, and is re-read on every poll so
  watchlist changes take effect without restarting the feed.
- **Pass `fallback_factory=SimulatorSource` explicitly.** Without it, the
  documented 401/403 auto-fallback to the simulator is inert — this was
  flagged in the code review and is the one open item left for this wiring.
- **Only `create_source()`, `MarketFeed`, `PriceCache`, `PriceUpdate`,
  `Quote`, and `MarketDataSource` are exported** from `app.market` (plus
  `SimulatorSource` needed above for the fallback factory, importable
  directly from `app.market.simulator`). `MassiveSource` is not meant to be
  constructed directly by application code — go through `create_source()` so
  the environment-variable branch stays confined to one function.
- **Portfolio valuation and trade execution** (per `PLAN.md` §6-8) should
  read prices via `cache.get(ticker)` or `cache.snapshot()`, not by calling a
  source's `fetch()` directly — that's what keeps them agnostic to which
  source is active and avoids duplicate polling.
- **The SSE endpoint** is already implemented: `create_stream_router(cache)`
  in `stream.py` returns an `APIRouter` exposing `GET /api/stream/prices`. It
  reads the cache on its own fixed 500ms schedule, decoupled from whatever
  the active source's poll interval is — sends a full snapshot to each new
  subscriber, then only tickers whose price actually changed.
