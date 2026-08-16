# Phase 2: Trading & Portfolio - Research

**Researched:** 2026-08-16
**Domain:** Backend transactional trade execution (FastAPI + stdlib `sqlite3`) and a live-derived portfolio view on the existing SSE frontend
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Trades fill at a server-authoritative price — the backend reads `PriceCache.get(ticker)` at the moment the trade is processed, never a client-supplied/displayed price. — **Reversibility:** costly — changing this later means renegotiating the trade API contract's trust boundary (client currently can't influence fill price at all; adding client-price trust would be a security-relevant change).
- **D-02:** Only tickers currently on the watchlist are tradable. The trade bar (or backend validation) rejects tickers with no live price in `PriceCache`, since watchlist add/remove doesn't ship until Phase 3. — **Reversibility:** reversible — Phase 3 can lift this restriction once arbitrary-ticker price lookup exists.
- **D-03:** Trade quantities are whole shares only in the trade bar's input validation. The `positions`/`trades` schema already stores quantity as `REAL` (unchanged) to support fractional LLM-initiated trades in Phase 4 without a migration. — **Reversibility:** reversible — purely a frontend/API input-validation choice; the schema doesn't need to change to lift this later.
- **D-04:** Rejected trades (insufficient cash, overselling) show an inline error near the trade bar (not a toast or banner), clearing on the next valid input. — **Reversibility:** reversible.

### Claude's Discretion

- Exact positions-table row behavior when a sell reduces a position to zero (remove row immediately vs. brief "closed" transition) — no strong preference expressed; use judgment, default to removing the row since PORT-03 says "reduces or removes the position."
- Portfolio total value's exact update cadence in the header (every SSE tick vs. debounced) — follow the existing price-flash/SSE cadence pattern from Phase 1 unless a reason emerges to diverge.

### Deferred Ideas (OUT OF SCOPE)

- Portfolio heatmap (treemap) — explicitly Phase 3 (PORT-08)
- P&L-over-time chart — explicitly Phase 3 (PORT-09)
- Any-ticker trading (beyond the watchlist) — deferred until Phase 3's watchlist management ships arbitrary-ticker price lookup

None — discussion stayed within phase scope beyond the above, which are already scoped to later phases by ROADMAP.md.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| PORT-01 | User starts with $10,000 in virtual cash | Already seeded by Phase 1's `_seed_user_profile()` (`[VERIFIED: backend/app/db/database.py:81-85]`); Phase 2 only needs `GET /api/portfolio` to surface it — see Pattern 3 |
| PORT-02 | User can buy shares at current market price — instant fill, no fees, no confirmation | `execute_trade()` design (Pattern 2), Pydantic `TradeRequest` (Code Examples), fill price from `PriceCache.get()` (D-01) |
| PORT-03 | User can sell shares they own at current market price — instant fill | Same `execute_trade()` path, `side="sell"` branch; zero-quantity row removal resolved by CONTEXT.md discretion |
| PORT-04 | Buying with insufficient cash is rejected with a clear error | Validation inside `execute_trade()` before any write, raising a domain exception mapped to HTTP 400 (Pitfall 3, Assumption A1); exact copy from `02-UI-SPEC.md` |
| PORT-05 | Selling more shares than owned is rejected with a clear error | Same validation path, oversell case; exact copy from `02-UI-SPEC.md` |
| PORT-06 | Positions table: ticker, quantity, avg cost, current price, unrealized P&L, % change | `GET /api/portfolio` response shape mirrors `_watchlist_entry()` (Pattern 3); `PositionsTable`/`PositionRow` mirror `Watchlist`/`WatchlistRow` |
| PORT-07 | Total portfolio value (cash + positions) updating live in header | Pattern 3 — client-side `derivePortfolioValue()` overlay on the SSE `prices` map, no new polling |
| PORT-10 | Trade history recorded append-only in `trades` table | `execute_trade()`'s single `BEGIN IMMEDIATE` transaction inserts one `trades` row per fill (Pattern 2); no update/delete path exists anywhere in this design |
| UI-03 | Trade bar lets user enter ticker/quantity and submit buy/sell with one click | `TradeBar.tsx` component structure (Recommended Project Structure); Copywriting Contract and disabled-state rules already locked in `02-UI-SPEC.md` |
| TEST-01 | Backend unit tests cover trade execution, P&L math, edge cases (insufficient cash, overselling) | Validation Architecture section — full requirement→test map and Wave 0 gaps below |

</phase_requirements>

## Summary

Phase 2 has almost no new-technology risk: no new packages are needed, no new services, no new infra. The whole phase is additive work inside a codebase whose conventions are already fully established by Phase 1 — `?`-placeholder SQL, `contextlib.closing()` connections, frozen dataclasses, factory-built `APIRouter`s, `run_in_threadpool` for sync DB calls in async routes, and a hand-built `<div role="button">` grid-row pattern on the frontend. The correct approach for this phase is almost entirely "extend the existing pattern," not "introduce a new one."

The one genuine technical risk is trade-execution correctness under concurrent requests: the trade endpoint must read `cash_balance`/`positions`, validate, and write in a single atomic unit, or two near-simultaneous trades (e.g., a slow double-click before the frontend's own in-flight-disable kicks in, per `02-UI-SPEC.md`) can produce a lost-update race where both requests read stale state and the second write silently clobbers the first. `database.py`'s existing `with closing(connect()) as conn, conn:` pattern commits correctly for a single statement group but does **not**, by itself, prevent this race — see Pitfall 1 below for the fix (`BEGIN IMMEDIATE`).

The second area needing a explicit architectural call is where "live" values come from. The header total value must move with every SSE price tick (success criterion 5). The correct, established pattern — already used by `Watchlist.tsx` for the watchlist — is: the backend returns a **snapshot** (`GET /api/portfolio`, computed once per request using `PriceCache.get()`), and the frontend re-derives live figures client-side by overlaying the already-flowing SSE `prices` map on top of that snapshot in a pure function, the same way `Watchlist.tsx` does `live?.price ?? entry.price`. No new polling loop, no new SSE channel, no backend push for portfolio values.

**Primary recommendation:** Add one new backend package `backend/app/portfolio/` (models + a pure trade-execution service + a router factory mirroring `create_stream_router`), wire it into `main.py` exactly where `/api/watchlist` is registered, and on the frontend add a `usePortfolioValue`-style pure derivation function plus `PositionsTable`/`PositionRow`/`TradeBar` components that mirror `Watchlist`/`WatchlistRow` exactly.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Trade fill price authority | API / Backend | — | D-01 (locked): backend reads `PriceCache.get(ticker)` at execution time; client price is never trusted |
| Trade validation (cash/shares/tradability) | API / Backend | Browser / Client | Backend is authoritative (security boundary); client does a cheap pre-check for UX responsiveness only (D-04, UI-SPEC "partial" state) |
| Cash balance / position persistence | Database / Storage | API / Backend | `users_profile.cash_balance`, `positions` rows — SQLite is the only source of truth, backend is the only writer |
| Trade history (append-only) | Database / Storage | API / Backend | `trades` table, insert-only, no update/delete path (PORT-10) |
| Portfolio snapshot computation (positions + P&L + total value) | API / Backend | — | `GET /api/portfolio` computes current_price/unrealized_pnl/% change server-side per position, mirroring the existing `/api/watchlist` `_watchlist_entry()` pattern |
| Live re-derivation of portfolio value between fetches | Browser / Client | — | Header total value "moves with every price tick" (success criterion 5) via client-side overlay of the SSE `prices` map onto the last-fetched snapshot — no new network round-trip per tick |
| Positions table rendering / trade bar UI | Browser / Client | — | Presentational; consumes the snapshot + live prices exactly as `Watchlist.tsx` does today |
| Error copy rendering | Browser / Client | API / Backend | Backend returns machine-checkable error detail; frontend renders the exact UI-SPEC copy inline near the trade bar (D-04) |

## Package Legitimacy Audit

No external packages are added in this phase. Trade execution uses Python's built-in `sqlite3` module and the already-installed `pydantic`/`fastapi` (transitively pinned via `fastapi>=0.115.0` in `backend/pyproject.toml`, resolved to `fastapi==0.141.1` / `pydantic==2.13.4` in the current environment — confirmed by running `uv run python -c "import fastapi, pydantic; ..."` in this session). No `npm install` / `uv add` / `pip install` is required for Phase 2. `npx shadcn add input` (already specified in `02-UI-SPEC.md`) adds a local component file over the already-installed `@base-ui/react` dependency — it is not a new npm package.

**Packages removed due to [SLOP] verdict:** none — no packages proposed.
**Packages flagged as suspicious [SUS]:** none — no packages proposed.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `sqlite3` (stdlib) | bundled with Python 3.12 | Trade transaction persistence | Already the project's only DB layer (`backend/app/db/database.py`); no ORM introduced per project convention |
| FastAPI | 0.141.1 (installed, `[VERIFIED: backend env, this session]`) | `/api/portfolio`, `/api/portfolio/trade` routes | Already the app framework; `APIRouter` factory pattern already established |
| Pydantic | 2.13.4 (installed, `[VERIFIED: backend env, this session]`) | Request body validation for `POST /api/portfolio/trade` | Ships transitively with FastAPI; already the implicit validation layer FastAPI routes rely on |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `starlette.concurrency.run_in_threadpool` | ships with `starlette` (FastAPI dep) | Run the synchronous `sqlite3` trade transaction from an `async def` route without blocking the event loop | Already used for `db.watchlist_tickers` in `main.py:47` `[VERIFIED: backend/app/main.py:47]` — the same pattern applies to every new DB-touching route |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `sqlite3` + hand-written transaction | SQLAlchemy Core/ORM | `CONCERNS.md` (stale, pre-Phase-1) suggested this; Phase 1 already established raw `sqlite3` as the project's DB layer, so introducing an ORM now would be an inconsistent, unrequested architecture change — do not do this |
| Custom exception + route-level `try/except` → `HTTPException` | FastAPI `@app.exception_handler` global handler | A global handler is worth it once there are 3+ distinct domain-error shapes across many routes; for 2 routes and 3 error cases, inline `try/except HTTPException` is simpler and matches "do not overengineer" (project CLAUDE.md) |

**Installation:** None required — no new dependencies.

**Version verification:** `fastapi` and `pydantic` versions confirmed installed in the backend's `uv` environment this session via `uv run python -c "import fastapi, pydantic; print(fastapi.__version__, pydantic.__version__)"` → `fastapi 0.141.1`, `pydantic 2.13.4`. `[VERIFIED: backend uv environment, this session]`

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Browser                                                          │
│                                                                   │
│  usePriceStream() ──SSE prices──┐                                │
│                                  ▼                                │
│  fetch /api/portfolio ──snapshot──► derivePortfolioValue()        │
│       (once on load,             (pure fn: cash + Σ qty×price)   │
│        again after each trade)         │                          │
│                                         ▼                          │
│                              Header total value (live)            │
│                              PositionsTable (live overlay)        │
│                                         │                          │
│  TradeBar ── POST /api/portfolio/trade ─┘  (ticker, side, qty)    │
└───────────────────────┬───────────────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼──────────────────────────────────────────┐
│ FastAPI (backend/app/main.py)                                     │
│                                                                     │
│  create_portfolio_router(cache) ──┐                                │
│    GET  /api/portfolio            │  read-only: compute snapshot   │
│    POST /api/portfolio/trade      │  read PriceCache.get(ticker) — │
│                                    │  never a market source directly│
│                                    ▼                                │
│                          app/portfolio/service.py                  │
│                    execute_trade(ticker, side, qty, cache)         │
│                    1. BEGIN IMMEDIATE (acquire write lock first)   │
│                    2. read cash_balance + position                 │
│                    3. validate (cash / shares / tradability)        │
│                    4. write positions + trades + users_profile     │
│                    5. COMMIT                                        │
└───────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────▼──────────────────────────────────────────┐
│ SQLite (db/finally.db)                                            │
│   users_profile.cash_balance | positions | trades (append-only)   │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
backend/app/portfolio/
├── __init__.py       # re-export public names, mirrors app/db/__init__.py and app/market/__init__.py
├── models.py          # frozen dataclasses: Position, TradeResult (+ custom exceptions)
├── service.py          # execute_trade(), get_portfolio() — the only code that touches positions/trades/users_profile tables
└── routes.py           # create_portfolio_router(cache) — mirrors app/market/stream.py's create_stream_router(cache)

frontend/lib/
└── portfolio.ts        # derivePortfolioValue(snapshot, prices) — pure fn, same shape as Watchlist's live-merge logic

frontend/components/
├── PositionsTable.tsx  # mirrors Watchlist.tsx (skeleton / empty / populated states, WATCHLIST_ROW_GRID-style constant)
├── PositionRow.tsx      # mirrors WatchlistRow.tsx
└── TradeBar.tsx          # new: ticker input, quantity input, Buy/Sell buttons, inline error text
```

### Pattern 1: Router factory bound to the shared cache (not `request.app.state`)
**What:** A function `create_portfolio_router(cache: PriceCache) -> APIRouter` that closes over the module-level `cache` object, called once at import time in `main.py` — the exact shape of `create_stream_router`.
**When to use:** Any new route that needs `PriceCache` access.
**Example:**
```python
# Source: backend/app/market/stream.py:49-65 [VERIFIED: backend/app/market/stream.py:49-65]
def create_stream_router(cache: PriceCache) -> APIRouter:
    """Build the `/api/stream/prices` router bound to a specific cache.

    A factory (rather than a module-level router reading `request.app.state`)
    keeps this endpoint independently testable without a full app lifespan.
    """
    router = APIRouter()

    @router.get("/api/stream/prices")
    async def stream_prices(request: Request) -> EventSourceResponse:
        return EventSourceResponse(price_events(cache))

    return router
```
Apply the identical shape for `create_portfolio_router(cache)`, registered in `main.py` the same way: `app.include_router(create_portfolio_router(cache))`, placed before the catch-all static mount (`main.py:73-81` establishes this ordering constraint — `[VERIFIED: backend/app/main.py:73-81]`).

### Pattern 2: `BEGIN IMMEDIATE` for the trade write path
**What:** Acquire SQLite's write lock *before* reading the values you're about to validate against, so a second concurrent trade request blocks until the first fully commits, rather than both reading stale data and racing to write.
**When to use:** `execute_trade()` only — the one code path in this phase that does read-then-conditionally-write.
**Example:**
```python
# Adapted from database.py's connection pattern [VERIFIED: backend/app/db/database.py:52-62]
# plus the transaction-control guidance below [CITED: docs.python.org/3/library/sqlite3.html]
import sqlite3
from contextlib import closing

def execute_trade(ticker: str, side: str, quantity: int, cache: PriceCache) -> TradeResult:
    quote = cache.get(ticker)
    if quote is None:
        raise UntradableTickerError(ticker)

    conn = sqlite3.connect(db_path(), isolation_level=None)  # autocommit off; we control BEGIN/COMMIT
    conn.row_factory = sqlite3.Row
    with closing(conn):
        conn.execute("BEGIN IMMEDIATE")  # acquire the write lock now, before any read
        try:
            row = conn.execute(
                "SELECT cash_balance FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
            ).fetchone()
            # ... validate against row["cash_balance"] and current position, using quote.price ...
            # ... UPDATE users_profile / INSERT OR REPLACE positions / INSERT trades ...
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
```
This is a deliberate departure from `database.py`'s `with closing(connect()) as conn, conn:` idiom (which is correct for `initialize()`'s single additive script, but leaves the transaction boundary to Python's legacy implicit-BEGIN-on-first-DML behavior — a plain read does not take the write lock, so two concurrent trade requests can both pass validation against stale data before either commits). `BEGIN IMMEDIATE` closes that gap. Keep `connect()`'s existing signature untouched for read-only routes (`GET /api/portfolio`) — this pattern is needed only where read-validate-write must be atomic.

### Pattern 3: Backend computes the snapshot, frontend overlays live prices — never re-fetch on every tick
**What:** `GET /api/portfolio` computes `current_price` / `unrealized_pnl` / `change_percent` per position using `PriceCache.get()` **once**, at request time — exactly like `_watchlist_entry()` does for `/api/watchlist`. The frontend fetches this once on load and again after each trade, then derives live-moving figures by merging the already-open SSE `prices` map on top of it in a pure function — exactly like `Watchlist.tsx` does today.
**When to use:** Header total value, positions table's "current price"/"unrealized P&L"/"% change" columns.
**Example (backend, mirrors the existing watchlist helper):**
```python
# Source: backend/app/main.py:51-70 [VERIFIED: backend/app/main.py:51-70]
def _watchlist_entry(ticker: str, update: PriceUpdate | None) -> dict:
    if update is None:
        return {"ticker": ticker, "price": None, ...}
    return {
        "ticker": ticker,
        "price": update.price,
        "change_percent": round(update.change_percent, 4),
        ...
    }
```
**Example (frontend, mirrors the existing live-merge in `Watchlist.tsx`):**
```typescript
// Source: frontend/components/Watchlist.tsx:46-49 [VERIFIED: frontend/components/Watchlist.tsx:46-49]
const live = prices[entry.ticker];
const price = live?.price ?? entry.price;
const changePercent = live?.change_percent ?? entry.change_percent;
const direction = live?.direction ?? entry.direction;
```
Apply the identical `live?.X ?? snapshot.X` merge to derive each position's live current price and, from that, the header's total portfolio value (`cash + Σ quantity × livePrice`) in a small pure function (e.g. `frontend/lib/portfolio.ts`), computed in a `useMemo` fed by the same `prices` object `page.tsx` already gets from `usePriceStream()` (`[VERIFIED: frontend/app/page.tsx:12]`) — no new SSE subscription, no polling interval, no extra network call per tick.

### Anti-Patterns to Avoid
- **Calling a market source's `fetch()` directly from trade execution:** Documented anti-pattern in `.planning/codebase/ARCHITECTURE.md` and reaffirmed by `02-CONTEXT.md` D-01/Reusable Assets — always `PriceCache.get(ticker)`.
- **Re-fetching `/api/portfolio` on a `setInterval` to make the header "live":** Defeats the whole point of the SSE stream already open on the page and duplicates work `Watchlist.tsx` already solved. Use the client-side overlay (Pattern 3) instead.
- **Read-then-write without `BEGIN IMMEDIATE` in trade execution:** See Pitfall 1 — silently produces a lost-update race under concurrent requests, not caught by any test that only exercises one trade at a time.
- **Trusting a client-supplied price field in the trade request body:** Explicitly forbidden by D-01 (locked decision) — the Pydantic request model for `POST /api/portfolio/trade` must not accept a `price` field at all.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request body validation (ticker/side/quantity shape) | Manual `dict` parsing + hand-written type checks | A Pydantic `BaseModel` with `Field(gt=0)` / `Literal["buy", "sell"]` | FastAPI already does this automatically once a route parameter is typed as a `BaseModel`; the app has zero manual JSON-body parsing anywhere today `[CITED: fastapi.tiangolo.com/tutorial/body-fields]` |
| Currency/percentage rounding | Rounding at every intermediate calculation step | `round(value, 2)` (or `4` for percents, matching existing convention) applied once, only at the API response boundary | Matches the exact precedent already in the codebase — `round(update.change_percent, 4)` is applied only when building the JSON payload, not during the math `[VERIFIED: backend/app/main.py:67 and backend/app/market/stream.py:42]` |
| Transaction retry/locking helpers for SQLite | A custom retry-loop wrapper or a third-party SQLite concurrency library (e.g. the `msqlite` package surfaced by web search) | `BEGIN IMMEDIATE` on the single connection used for the trade (Pattern 2) | Single-user app, single writer — a third-party locking library is unnecessary complexity for a problem `BEGIN IMMEDIATE` already solves at the SQL level `[CITED: docs.python.org/3/library/sqlite3.html]` |
| UUID / timestamp generation for new `positions`/`trades` rows | Any custom ID/timestamp scheme | `uuid.uuid4().hex` and `datetime.now(UTC).isoformat()` | Exact existing convention, already used for every other table `[VERIFIED: backend/app/db/database.py:92, 110-111]` |

**Key insight:** every "don't hand-roll" item in this phase already has a working precedent *in this exact codebase* from Phase 1 — the task is pattern-matching, not invention.

## Common Pitfalls

### Pitfall 1: Lost-update race on concurrent trade requests
**What goes wrong:** Two trade requests for the same ticker/user arrive close together (e.g., a double-click before the UI-SPEC's in-flight button-disable takes effect, or — architecturally more important — any future caller such as Phase 4's LLM-initiated trades running concurrently with a manual trade). Both read the same `cash_balance` before either commits, both pass validation, and the second commit overwrites the first's cash/position update instead of building on it — cash ends up wrong, silently.
**Why it happens:** `sqlite3.connect()`'s default (legacy) transaction control only begins an implicit transaction on the *first write statement*, not on the first read. A plain `SELECT` takes no lock, so two concurrent connections can both read stale state before either writes `[CITED: docs.python.org/3/library/sqlite3.html]`.
**How to avoid:** Use Pattern 2 — `isolation_level=None` (autocommit) plus an explicit `BEGIN IMMEDIATE` issued *before* the first read in `execute_trade()`, so the second request's transaction blocks (up to the connection's `timeout`, default 5s) until the first fully commits, then reads fresh state.
**Warning signs:** A test that only ever calls `execute_trade()` once per test will never catch this — a dedicated concurrency test (two `execute_trade()` calls interleaved, or run via `asyncio.gather`) is needed to prove the fix, and TEST-01 explicitly asks for "edge cases," which should include this one.

### Pitfall 2: Ticker case mismatch between trade request and `PriceCache`
**What goes wrong:** `PriceCache` keys are whatever `DEFAULT_TICKERS` uses — all uppercase (`AAPL`, `GOOGL`, …) `[VERIFIED: backend/app/db/database.py:20-31]`. If a trade request arrives with a lowercase or mixed-case ticker, `cache.get(ticker)` returns `None` and the trade is wrongly rejected as "not on your watchlist" even though the ticker is genuinely tradable.
**Why it happens:** No normalization currently exists anywhere in the codebase (the watchlist route just round-trips whatever `db.watchlist_tickers()` returns, which is always already uppercase because it was seeded that way).
**How to avoid:** Normalize the incoming `ticker` to uppercase in the Pydantic request model (a `field_validator`) or immediately at the top of `execute_trade()`, before the `PriceCache.get()` lookup.
**Warning signs:** A trade for a valid watchlist ticker fails with the "isn't on your watchlist" error (UI-SPEC copy) despite the ticker being correct — check casing first.

### Pitfall 3: Conflating FastAPI's automatic 422 with a domain rejection
**What goes wrong:** Using `HTTPException(status_code=422, ...)` for "insufficient cash" / "overselling" makes it indistinguishable, from the frontend's error-handling code, from FastAPI's own automatic 422 `RequestValidationError` (malformed JSON, wrong types) `[CITED: fastapi.tiangolo.com/tutorial/handling-errors]`.
**Why it happens:** 422 feels like the generic "something about this request is wrong" status, but FastAPI reserves it specifically for request-shape validation failures it generates itself.
**How to avoid:** Raise domain rejections (insufficient cash, overselling, untradable ticker) as `HTTPException(status_code=400, detail=...)` from inside the route handler after catching the service-layer exception — 400 unambiguously means "the request was well-formed but the trade was refused," leaving 422 exclusively for Pydantic schema failures. This is a recommendation, not verified against an explicit requirement — flagged in the Assumptions Log.
**Warning signs:** Frontend error-handling code that can't distinguish "you mistyped the request" from "you don't have enough cash" without parsing `detail` text.

### Pitfall 4: Scope creep into `portfolio_snapshots` / `PORT-08`/`PORT-09`
**What goes wrong:** It's tempting to add the 30-second snapshot-recording background task and `GET /api/portfolio/history` while touching `portfolio_snapshots`-adjacent code, since the table already exists.
**Why it happens:** The table is right there, already seeded/created by Phase 1's lazy init, and PLAN.md describes the snapshot cadence in the same breath as the trade endpoints.
**How to avoid:** `02-CONTEXT.md`'s Phase Boundary and `REQUIREMENTS.md`'s traceability table are explicit and locked: PORT-08 (heatmap) and PORT-09 (P&L chart, including its "recorded every 30s and after each trade" snapshot-writing task) are Phase 3, not Phase 2. Phase 2 touches `positions`, `trades`, and `users_profile.cash_balance` only. Do not add a snapshot-writing background task or `/api/portfolio/history` this phase.
**Warning signs:** A plan task mentions `portfolio_snapshots` inserts or a 30-second timer — cross-check against `REQUIREMENTS.md`'s traceability table before including it.

## Code Examples

### Trade request Pydantic model (whole-share constraint honoring D-03)
```python
# Illustrative — not fetched from a live doc, follows the confirmed
# FastAPI/Pydantic Field pattern [CITED: fastapi.tiangolo.com/tutorial/body-fields]
from typing import Literal
from pydantic import BaseModel, Field

class TradeRequest(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)  # whole shares only, per D-03 — the manual trade bar's constraint.
    # No `price` field: D-01 forbids a client-supplied fill price.
```
Note: `positions.quantity` and `trades.quantity` are `REAL` in the schema `[VERIFIED: backend/app/db/schema.sql:23, 34]` specifically to support Phase 4's fractional LLM-initiated trades without a migration (per `02-CONTEXT.md` D-03). Keep the **service function** (`execute_trade`) typed to accept `float` so Phase 4 can call it directly with a fractional quantity; only this endpoint's **request model** constrains to `int`.

### Existing DB connection pattern to extend (read-only routes)
```python
# Source: backend/app/db/database.py:52-62, 96-107 [VERIFIED: backend/app/db/database.py:52-62, 96-107]
def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def watchlist_tickers() -> list[str]:
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY rowid",
            (DEFAULT_USER_ID,),
        ).fetchall()
    return [row["ticker"] for row in rows]
```
`GET /api/portfolio` (read-only, no write) should follow this exact `connect()` + `closing()` shape — only `execute_trade()`'s write path needs the `BEGIN IMMEDIATE` variant from Pattern 2.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `isolation_level` string (`""`, `"DEFERRED"`, `"EXCLUSIVE"`, `"IMMEDIATE"`, or `None`) as the only transaction-control knob | Python 3.12 added a first-class `Connection.autocommit` attribute (PEP 249-style) alongside the legacy `isolation_level`; the legacy default (`LEGACY_TRANSACTION_CONTROL`) is still default for now, with a documented future change | Python 3.12 (this project's minimum supported version, `[VERIFIED: backend/pyproject.toml:6]`) | Both knobs exist simultaneously on 3.12; this research recommends the explicit `isolation_level=None` + manual `BEGIN`/`COMMIT` idiom (Pattern 2) rather than relying on the legacy default's implicit-begin-on-first-write behavior, precisely because that default doesn't lock on read |

**Deprecated/outdated:** None specific to this phase — the codebase's existing `sqlite3` usage (`database.py`) is current and correct for its use case (additive schema init); it simply doesn't need the stronger locking that trade execution does.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Domain trade rejections (insufficient cash, overselling, untradable ticker) should return HTTP 400, reserving 422 for FastAPI's own Pydantic schema-validation failures | Common Pitfalls #3, Architecture Patterns | Low — either status code works functionally as long as the frontend checks `detail` text (per UI-SPEC's exact copy strings) rather than branching on status code; worth confirming with the planner/user if a stricter API contract convention is wanted |
| A2 | Positions table's "current price"/"unrealized P&L"/"% change" columns should live-update via the same SSE overlay as the header, even though only the header's live update is an explicit success criterion | Architecture Patterns, Pattern 3 | Low — if not done, the positions table would only refresh after each trade/page load rather than every tick; visually inconsistent with the header but not a functional defect against the stated success criteria |
| A3 | `execute_trade()` should accept `float` quantity at the service layer (even though this phase's endpoint types the request as `int`), to avoid a signature change when Phase 4 adds fractional LLM-initiated trades | Code Examples | Low — reversible; if Phase 4 instead builds an entirely separate execution path, this forward-compatibility choice costs nothing now |

## Open Questions

1. **Should `POST /api/portfolio/trade` and the internal `execute_trade()` be the exact function Phase 4's LLM chat flow reuses, or will Phase 4 introduce a parallel path?**
   - What we know: PLAN.md §9 states LLM-initiated trades "go through the same validation as manual trades."
   - What's unclear: Whether that means literally calling `execute_trade()`, or re-implementing equivalent validation in the chat flow.
   - Recommendation: Design `execute_trade(ticker, side, quantity, cache)` as a plain, HTTP-agnostic function in `app/portfolio/service.py` (not embedded in the route handler) specifically so Phase 4 can import and call it directly — low cost now, removes a real risk of validation drift later.

2. **HTTP status code convention for domain trade rejections (400 vs 422)** — see Assumption A1. Not blocking; either choice is internally consistent as long as it's applied uniformly to all three rejection cases (PORT-04, PORT-05, D-02's untradable-ticker case).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Backend runtime, `sqlite3` autocommit attribute (Pattern 2) | ✓ | confirmed via `uv run python --version` in this session's env resolution (project requires `>=3.12`, `[VERIFIED: backend/pyproject.toml:6]`) | — |
| `sqlite3` stdlib module | All persistence | ✓ | bundled with Python, no separate install | — |
| FastAPI / Pydantic | Route + request validation | ✓ | `fastapi==0.141.1`, `pydantic==2.13.4` `[VERIFIED: backend uv environment, this session]` | — |
| `uv --extra dev` | Running backend tests (TEST-01) | ✓ (assumed present per Phase 1's successful test runs; see project MEMORY note that plain `uv run pytest` silently skips `pytest-asyncio`) | — | Always run `uv run --extra dev pytest`, never bare `uv run pytest` |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — the only environment gotcha is the `--extra dev` pytest flag, which is a command-invocation convention, not a missing dependency (documented in project memory: `backend-pytest-needs-dev-extra.md`).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (`[VERIFIED: backend/pyproject.toml:19]` pins `pytest>=8.3.0`; installed resolved version per `.claude/CLAUDE.md`'s Technology Stack section is 9.1.1) |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` (`[VERIFIED: backend/pyproject.toml:32-38]`) |
| Quick run command | `uv run --extra dev pytest tests/portfolio/ -v` (new test dir, mirrors `tests/market/`) |
| Full suite command | `uv run --extra dev pytest -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PORT-01 | Fresh user has $10,000 cash | integration | `uv run --extra dev pytest tests/test_app.py -k cash -x` | ❌ Wave 0 (extend `test_app.py` or add `tests/portfolio/test_routes.py`) |
| PORT-02 | Buy fills at cache price, cash decreases, position created | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k buy -x` | ❌ Wave 0 |
| PORT-03 | Sell fills at cache price, cash increases, position reduced/removed | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k sell -x` | ❌ Wave 0 |
| PORT-04 | Insufficient cash rejected, state unchanged | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k insufficient_cash -x` | ❌ Wave 0 |
| PORT-05 | Overselling rejected, state unchanged | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k oversell -x` | ❌ Wave 0 |
| PORT-06 | `GET /api/portfolio` shape: ticker/qty/avg_cost/price/pnl/% change | integration | `uv run --extra dev pytest tests/portfolio/test_routes.py -k shape -x` | ❌ Wave 0 |
| PORT-07 | Total value = cash + Σ(qty × current price) | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k total_value -x` | ❌ Wave 0 |
| PORT-10 | Every trade appends a `trades` row, never updates/deletes | unit | `uv run --extra dev pytest tests/portfolio/test_service.py -k trade_history -x` | ❌ Wave 0 |
| UI-03 | Trade bar submits buy/sell with one click | manual/UAT this phase | — (frontend unit-test coverage for this component is `TEST-03`, explicitly Phase 3 per `REQUIREMENTS.md` traceability — do not add it early) | n/a |
| TEST-01 | Backend covers trade execution, P&L math, edge cases | (umbrella — see PORT-02..05, 07, 10 above) | `uv run --extra dev pytest tests/portfolio/ -v` | ❌ Wave 0 |

Concurrency (Pitfall 1) is not itself a numbered requirement but is essential to TEST-01's "edge cases" language — include a dedicated concurrent-trade test in Wave 0 alongside the requirement-mapped tests.

### Sampling Rate
- **Per task commit:** `uv run --extra dev pytest tests/portfolio/ -v`
- **Per wave merge:** `uv run --extra dev pytest -v` (full backend suite, includes `tests/market/`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/portfolio/__init__.py` — new test package, mirrors `tests/market/`
- [ ] `backend/tests/portfolio/test_service.py` — covers PORT-02, PORT-03, PORT-04, PORT-05, PORT-07, PORT-10, and the concurrent-trade race case
- [ ] `backend/tests/portfolio/test_routes.py` — covers PORT-01, PORT-06 (`GET /api/portfolio` shape and status codes), plus `POST /api/portfolio/trade`'s HTTP-layer error mapping
- [ ] No new fixtures needed beyond the existing `_use_tmp_db(tmp_path, monkeypatch)` helper already in `tests/test_app.py` `[VERIFIED: backend/tests/test_app.py:7-9]` — reuse it

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | None — project is explicitly zero-auth, single `user_id="default"` (project CLAUDE.md constraint) |
| V3 Session Management | no | Same as above |
| V4 Access Control | no | Single-user; no cross-user boundary exists to enforce this phase |
| V5 Input Validation | yes | Pydantic `BaseModel` with `Field(gt=0)` / `Literal["buy","sell"]` for `POST /api/portfolio/trade`; server-side ticker normalization + `PriceCache.get()` membership check (D-02) rather than trusting client-declared tradability |
| V6 Cryptography | no | No secrets or crypto touched this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| SQL injection via ticker/side strings in the trade path | Tampering | `?`-placeholder parameterized queries only — the same pattern `database.py` and Phase 1's `01-SECURITY.md` already established project-wide; never string-format SQL `[VERIFIED: backend/app/db/database.py:82-93]` |
| Client-supplied fill price overriding the server's authoritative price | Tampering / Elevation of Privilege (of a sort — a user could self-grant favorable fills) | D-01 (locked): the `TradeRequest` Pydantic model must not declare a `price` field at all; the route must never read a price from the request body |
| Lost-update race under concurrent trade requests | Tampering (of financial state, unintentional but still a data-integrity violation) | `BEGIN IMMEDIATE` transaction (Pattern 2 / Pitfall 1) |
| Malformed/negative/zero quantity in trade requests | Tampering | Pydantic `Field(gt=0)` + `int` typing rejects zero, negative, and fractional quantities before any DB access |

## Sources

### Primary (HIGH confidence)
- `backend/app/db/database.py`, `backend/app/db/schema.sql`, `backend/app/market/cache.py`, `backend/app/market/models.py`, `backend/app/market/stream.py`, `backend/app/main.py`, `backend/tests/test_app.py`, `backend/tests/conftest.py` — read in full this session
- `frontend/components/WatchlistRow.tsx`, `frontend/components/PriceCell.tsx`, `frontend/components/Watchlist.tsx`, `frontend/components/Header.tsx`, `frontend/app/page.tsx`, `frontend/lib/usePriceStream.ts`, `frontend/lib/types.ts`, `frontend/lib/format.ts`, `frontend/components/ui/button.tsx`, `frontend/components/ui/skeleton.tsx` — read in full this session
- `.planning/phases/02-trading-portfolio/02-CONTEXT.md`, `.planning/phases/02-trading-portfolio/02-UI-SPEC.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/config.json` — read in full this session
- `uv run python -c "import fastapi, pydantic; ..."` executed in this session's backend environment — confirmed installed versions

### Secondary (MEDIUM confidence)
- Context7 `/websites/fastapi_tiangolo` — Pydantic `Field`/`BaseModel` request-body validation and `HTTPException` vs. automatic `RequestValidationError` distinction
- WebSearch cross-checked against `docs.python.org/3/library/sqlite3.html` (appeared as a primary result and was reflected in the synthesized answer) — Python 3.12 `autocommit` attribute and `isolation_level=None` + explicit `BEGIN`/`COMMIT` transaction control

### Tertiary (LOW confidence)
- WebSearch on "database is locked" mitigation (WAL mode, `busy_timeout`, third-party libraries like `msqlite`) — general SQLite concurrency background; the specific recommendation adopted in this document (`BEGIN IMMEDIATE`) is drawn from the higher-confidence Python docs source, not this tertiary search, and is architecturally simpler than the WAL/pragma tuning these results suggested for this phase's single-writer, low-volume scope

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; every recommendation matches an existing, verified in-repo pattern
- Architecture: HIGH — router-factory and live-overlay patterns are directly copied from working Phase 1 code, not invented
- Pitfalls: MEDIUM — the `BEGIN IMMEDIATE` concurrency fix is grounded in official Python docs content surfaced via web search (not a directly fetched doc page), so tagged CITED rather than VERIFIED

**Research date:** 2026-08-16
**Valid until:** 30 days (stable stdlib/FastAPI APIs; re-check if `backend/pyproject.toml`'s FastAPI/Pydantic pins change)
