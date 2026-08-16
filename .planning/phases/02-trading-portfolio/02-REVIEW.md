---
phase: 02-trading-portfolio
reviewed: 2026-08-16T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - backend/app/main.py
  - backend/app/portfolio/__init__.py
  - backend/app/portfolio/models.py
  - backend/app/portfolio/routes.py
  - backend/app/portfolio/service.py
  - backend/tests/portfolio/test_routes.py
  - backend/tests/portfolio/test_service.py
  - frontend/app/globals.css
  - frontend/app/page.tsx
  - frontend/components/Header.tsx
  - frontend/components/PositionRow.tsx
  - frontend/components/PositionsTable.tsx
  - frontend/components/TradeBar.tsx
  - frontend/components/ui/input.tsx
  - frontend/lib/portfolio.test.ts
  - frontend/lib/portfolio.ts
  - frontend/lib/trade.test.ts
  - frontend/lib/trade.ts
  - frontend/lib/types.ts
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-08-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Reviewed the trade-execution backend (`app/portfolio/*`), its tests, and the frontend trade bar / positions table / portfolio-derivation layer. The `BEGIN IMMEDIATE` transaction pattern for `execute_trade` correctly serializes concurrent trades (verified: ruff clean, `tsc --noEmit` clean, eslint clean, full portfolio test suite green, and I independently reproduced the concurrency behavior at the sqlite3 level). No critical/security-level defects were found — trades are parameterized, quantity/side are constrained at the API boundary, and the frontend never sends a client-supplied fill price (D-01 upheld).

The issues found are all robustness/quality gaps, not exploitable bugs in the current phase's reachable code paths:

1. The transaction's exception handler can mask the real error with a second, more confusing error when lock acquisition itself fails.
2. `execute_trade`, despite being documented as the shared entry point for a future (Phase 4) caller, enforces none of its own invariants (positive quantity, valid side, normalized ticker) — it relies entirely on the Pydantic layer that only the current HTTP caller passes through.
3. `app/main.py` holds `cache` as a module-level singleton shared by every `TestClient(app)` instantiation across the test session, which is a fragile pattern for future parallel/isolated test runs.

Two minor code-quality items are also listed under Info.

## Warnings

### WR-01: Lock-acquisition failure in `execute_trade` masks the original error and isn't mapped to a client-safe response

**File:** `backend/app/portfolio/service.py:37-65`
**Issue:** `execute_trade` opens a raw connection and issues `BEGIN IMMEDIATE` inside the `try` block, then rolls back unconditionally in `except Exception`. If `BEGIN IMMEDIATE` itself fails (e.g., `sqlite3.OperationalError: database is locked` after the connection's 5s busy timeout expires under sustained contention — exactly the scenario `BEGIN IMMEDIATE` was introduced to guard, per `02-RESEARCH.md` Pitfall 1), no transaction is open yet, and the subsequent `conn.execute("ROLLBACK")` itself raises `sqlite3.OperationalError: cannot rollback - no transaction is active`, which replaces (masks) the original, more informative error. I reproduced this directly:
```
BEGIN failed: <class 'sqlite3.OperationalError'> database is locked
ROLLBACK ALSO FAILED: <class 'sqlite3.OperationalError'> cannot rollback - no transaction is active
```
Separately, neither the original nor the masking error is a `TradeRejected`, so `routes.py`'s `except TradeRejected` (routes.py:44) never catches it — the request falls through to an unhandled 500 with no domain-meaningful `detail` for the frontend's `tradeErrorMessage()` to render, even though this is a legitimate, expectable condition (lock contention) the module was specifically designed to handle gracefully.
**Fix:** Track whether the transaction actually started before attempting rollback, and let a lock-acquisition failure surface as a distinct, catchable condition:
```python
with closing(sqlite3.connect(db_path(), isolation_level=None)) as conn:
    conn.row_factory = sqlite3.Row
    began = False
    try:
        conn.execute("BEGIN IMMEDIATE")
        began = True
        ...
        conn.execute("COMMIT")
    except Exception:
        if began:
            conn.execute("ROLLBACK")
        raise
```
Consider also catching `sqlite3.OperationalError` in `routes.py` and mapping it to a 503/"try again" response rather than letting it become an opaque 500.

### WR-02: `execute_trade` enforces none of its own invariants despite being documented as the shared domain entry point

**File:** `backend/app/portfolio/service.py:24-57`
**Issue:** The docstring (lines 27-30) states `quantity` is typed `float` specifically because "Phase 4 adds fractional LLM-initiated trades and should not need a signature change" — i.e., this function is designed to be called directly by a future caller that bypasses `TradeRequest`'s Pydantic constraints (`Field(gt=0)`, `Literal["buy", "sell"]`, and the client-side `.trim().toUpperCase()` in `frontend/lib/trade.ts`). Today the only caller is `routes.py`, which happens to enforce all of these, so the gap isn't reachable yet — but the function itself:
- Never rejects `quantity <= 0`. A `side="buy"` with a negative quantity produces a negative `cost` (line 43), which passes the `cost > cash_balance` check trivially and *increases* cash while writing a negative-quantity buy into `positions`/`trades` (via `_apply_buy`, line 143).
- Never rejects an unrecognized `side` up front — it raises a bare `ValueError` mid-transaction (line 57) instead of a `TradeRejected` subclass, so a future caller gets an unmapped exception type instead of a domain error.
- Never trims/normalizes the ticker beyond `.upper()` (line 31) — a caller passing `" AAPL"` gets a spurious `UntradableTickerError` instead of a working trade.

**Fix:** Validate `quantity > 0` and `side in {"buy", "sell"}` at the top of `execute_trade`, before opening the connection, raising a `TradeRejected` subclass (or a new one) for both — and `.strip()` the ticker alongside `.upper()`. This keeps the invariant with the domain function rather than depending on every future caller re-deriving it:
```python
def execute_trade(ticker: str, side: str, quantity: float, cache: PriceCache) -> TradeResult:
    ticker = ticker.strip().upper()
    if side not in ("buy", "sell"):
        raise ValueError(f"unsupported trade side: {side!r}")
    if quantity <= 0:
        raise ValueError(f"quantity must be positive, got {quantity!r}")
    ...
```
(Or introduce a dedicated `TradeRejected` subclass if Phase 4 should surface this to the LLM as a domain rejection rather than a 500.)

### WR-03: Module-level `PriceCache` singleton in `app/main.py` is shared across every `TestClient(app)` instantiation in the test process

**File:** `backend/app/main.py:19`
**Issue:** `cache = PriceCache()` is created once at import time and is never reset. Every test that does `with TestClient(app) as client:` starts a fresh `MarketFeed` (via `lifespan`) writing into this same shared cache object, and the feed from a prior test is only stopped, not cleared, after `__exit__`. Today's tests happen to pass because every test seeds the same default watchlist tickers and only asserts loosely ("some price exists" / "cost is way more than cash"), so stale entries from a previous test are harmless. But this is a latent test-isolation hazard: it silently defeats "wait for a fresh price" polling loops (e.g. `test_routes.py:31-34`, which will now pass on the very first iteration because the cache is pre-warmed by a previous test rather than by the feed under test), and it will produce genuine cross-test races if tests are ever run with `pytest-xdist`'s `-n` in the same process/pool, or if a future test asserts on the *contents* of a fresh cache rather than just its non-emptiness.
**Fix:** Either give `PriceCache` a `clear()`/reset method invoked in a test fixture, or (better for testability) build the cache inside `lifespan`/`app.state` from a factory rather than a module-level global, so each `TestClient(app)` — or at least each test session that wants isolation — can inject its own instance. This is pre-existing Phase 1 architecture, not introduced by this phase, but Phase 2 adds `create_portfolio_router(cache)` on top of the same singleton and several new tests that rely on cache freshness, so it's worth flagging now rather than after a flaky-test incident.

## Info

### IN-01: `MAX_TICKER_LENGTH` / `TICKER_MAX_LENGTH` constant duplicated across two frontend files

**File:** `frontend/lib/trade.ts:7`, `frontend/components/TradeBar.tsx:12`
**Issue:** The ticker length limit `5` is defined independently in both files under different names (`MAX_TICKER_LENGTH` in `trade.ts`, `TICKER_MAX_LENGTH` in `TradeBar.tsx`). They currently agree, but nothing enforces that they stay in sync if one changes.
**Fix:** Export the constant from `lib/trade.ts` and import it into `TradeBar.tsx` for the `maxLength` prop, so there's a single source of truth.

### IN-02: `tradeErrorMessage`'s insufficient-cash sentence silently degrades to an em dash if `cash_balance` is missing/non-numeric

**File:** `frontend/lib/trade.ts:50-53`
**Issue:** `formatPrice(cashBalance)` where `cashBalance` falls back to `null` when `payload.cash_balance` isn't a number produces the sentence `"Not enough cash — this trade costs more than your $— available."` — grammatically odd and unhelpful. Not reachable today since the backend's `InsufficientCashError.detail()` (`backend/app/portfolio/models.py:60-66`) always includes a numeric `cash_balance`, but the type is `unknown` at this boundary by design, so a future backend change or a hand-crafted request against a permissive proxy could trigger it.
**Fix:** Fall back to the neutral default message (as the `default:` branch already does) when `cash_balance` isn't a number, rather than interpolating an em dash into an otherwise well-formed sentence.

---

_Reviewed: 2026-08-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
