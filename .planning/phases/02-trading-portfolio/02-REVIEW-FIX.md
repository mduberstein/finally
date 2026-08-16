---
phase: 02-trading-portfolio
fixed_at: 2026-08-16T06:15:00Z
review_path: .planning/phases/02-trading-portfolio/02-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-08-16T06:15:00Z
**Source review:** .planning/phases/02-trading-portfolio/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (fix_scope: critical_warning -- WR-01, WR-02, WR-03; IN-01/IN-02 out of scope)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: Lock-acquisition failure in `execute_trade` masks the original error and isn't mapped to a client-safe response

**Files modified:** `backend/app/portfolio/service.py`, `backend/app/portfolio/routes.py`
**Commit:** `8d29a5f`
**Applied fix:** Added a `began` flag in `execute_trade`, set only after `BEGIN IMMEDIATE` succeeds. The `except` block now only issues `ROLLBACK` when a transaction actually started, so a lock-acquisition failure (`sqlite3.OperationalError: database is locked`) propagates as itself instead of being masked by `cannot rollback - no transaction is active`. Also added an `except sqlite3.OperationalError` handler in the `/api/portfolio/trade` route that maps the condition to a 503 with a `database_busy` code, instead of letting it fall through to an opaque 500.

### WR-02: `execute_trade` enforces none of its own invariants despite being documented as the shared domain entry point

**Files modified:** `backend/app/portfolio/service.py`, `backend/app/portfolio/models.py`
**Commit:** `e0d78fb`
**Applied fix:** Added a new `InvalidTradeError` (a `TradeRejected` subclass, so it's automatically caught by the existing 400 handler in `routes.py`) and validate `side in {"buy", "sell"}` and `quantity > 0` at the top of `execute_trade`, before opening the connection. Also changed ticker normalization from `.upper()` to `.strip().upper()`. Removed the now-unreachable `else: raise ValueError(...)` branch inside the transaction since `side` is guaranteed valid by the time it's reached.

### WR-03: Module-level `PriceCache` singleton in `app/main.py` is shared across every `TestClient(app)` instantiation in the test process

**Files modified:** `backend/app/market/cache.py`, `backend/tests/conftest.py`, `backend/tests/market/test_cache.py`
**Commit:** `c404d1a`
**Applied fix:** Added `PriceCache.clear()` and a new autouse fixture (`_clean_price_cache`) in the top-level `tests/conftest.py` that clears `app.main.cache` before and after every test, so stale price entries from a prior test's feed can no longer pre-warm a "wait for a fresh price" polling loop in a later test. Also added two unit tests for the new `clear()` method in `tests/market/test_cache.py`. Chose the fixture-reset approach over rebuilding the cache from a factory inside `lifespan`/`app.state` (the review's alternative option) since it fixes the concrete test-isolation hazard without the larger, riskier refactor of moving router construction out of module-import time.

## Skipped Issues

None -- all in-scope findings were fixed.

---

_Fixed: 2026-08-16T06:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
