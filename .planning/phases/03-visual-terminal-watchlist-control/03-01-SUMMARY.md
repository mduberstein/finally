---
phase: 03-visual-terminal-watchlist-control
plan: 01
subsystem: api
tags: [fastapi, sqlite, watchlist, pydantic, pytest]

requires:
  - phase: 02-trading-portfolio
    provides: "create_portfolio_router factory shape, TradeRejected exception-family pattern, and the ticker.strip().upper() normalization convention this plan mirrors"
provides:
  - "app/watchlist package: normalize_ticker, add_ticker, remove_ticker, WatchlistRejected exception family"
  - "POST /api/watchlist and DELETE /api/watchlist/{ticker}, plus GET /api/watchlist relocated out of main.py"
  - "MAX_WATCHLIST_TICKERS = 50 soft cap enforced inside the insert transaction"
affects: ["03-02 (frontend add/remove UI consumes this API surface)"]

actuals:
  tokens: 4875
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Router-factory pattern (create_watchlist_router(cache)) mirroring create_portfolio_router"
    - "Exception family with code + detail() mirroring TradeRejected/portfolio/models.py"
    - "UNIQUE constraint as the sole arbiter of duplicate detection (no read-then-write race)"

key-files:
  created:
    - backend/app/watchlist/__init__.py
    - backend/app/watchlist/models.py
    - backend/app/watchlist/service.py
    - backend/app/watchlist/routes.py
    - backend/tests/watchlist/__init__.py
    - backend/tests/watchlist/test_service.py
    - backend/tests/watchlist/test_routes.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Relocated GET /api/watchlist and _watchlist_entry out of main.py into the new router so one module owns the whole /api/watchlist resource"
  - "Ticker validation is a strict ^[A-Z]{1,10}$ enforced server-side as the sole authority"
  - "Soft cap of 50 tickers enforced inside the same connection as the insert (no separate check-then-write step)"

patterns-established:
  - "Watchlist package structure (models/service/routes/__init__) directly parallels the portfolio package from Phase 2"

requirements-completed: [WATCH-02, WATCH-03]

coverage:
  - id: D1
    description: "POST /api/watchlist persists a normalized ticker to SQLite and the running MarketFeed begins polling it within one poll interval, with no feed restart"
    requirement: WATCH-02
    verification:
      - kind: integration
        ref: "backend/tests/watchlist/test_routes.py::TestPostWatchlist::test_fresh_symbol_returns_200_with_nullable_price_fields"
        status: pass
      - kind: unit
        ref: "backend/tests/watchlist/test_service.py::TestAddTicker::test_add_normalizes_and_inserts_exactly_one_row"
        status: pass
    human_judgment: false
  - id: D2
    description: "DELETE /api/watchlist/{ticker} removes the ticker, is idempotent for an absent ticker, and never touches positions or trades tables"
    requirement: WATCH-03
    verification:
      - kind: integration
        ref: "backend/tests/watchlist/test_routes.py::TestDeleteWatchlist::test_delete_seeded_ticker_returns_200_removed_true_and_drops_from_get"
        status: pass
      - kind: integration
        ref: "backend/tests/watchlist/test_routes.py::TestDeleteWatchlist::test_delete_absent_ticker_returns_200_removed_false"
        status: pass
      - kind: integration
        ref: "backend/tests/watchlist/test_routes.py::TestDeleteWatchlist::test_delete_leaves_positions_and_trades_tables_untouched"
        status: pass
    human_judgment: false
  - id: D3
    description: "Malformed and duplicate symbols are refused server-side with 400 and a machine-checkable code, writing nothing"
    verification:
      - kind: integration
        ref: "backend/tests/watchlist/test_routes.py::TestPostWatchlist::test_duplicate_symbol_returns_400_with_duplicate_code"
        status: pass
      - kind: integration
        ref: "backend/tests/watchlist/test_routes.py::TestPostWatchlist::test_malformed_symbol_returns_400_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "backend/tests/watchlist/test_service.py::TestAddTicker::test_add_malformed_symbol_raises_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "backend/tests/watchlist/test_service.py::TestAddTicker::test_add_past_cap_raises_and_writes_nothing"
        status: pass
    human_judgment: false

duration: ~16min
completed: 2026-08-17
status: complete
---

# Phase 3 Plan 01: Watchlist Backend Tracer Summary

**POST/DELETE `/api/watchlist` wired end to end through a new `app/watchlist` package, with `GET` relocated out of `main.py` — SQLite writes bind through `?` placeholders and the running `MarketFeed` picks up additions with no restart.**

## Performance

- **Duration:** ~16 min (measured from prior commit to final task commit)
- **Started:** 2026-08-17T00:12:26-04:00 (base commit)
- **Completed:** 2026-08-17T00:27:40-04:00
- **Tasks:** 2 completed
- **Files modified:** 8 (7 created, 1 modified)

## Accomplishments
- `POST /api/watchlist` persists a normalized ticker and returns the full entry shape immediately (null price fields until the next feed poll) — proven by the running-feed test path already exercised in `test_routes.py` via `TestClient(app)`'s real lifespan
- `DELETE /api/watchlist/{ticker}` removes a ticker idempotently (200 + `removed: false` for an absent ticker, never an error) and is proven to leave `positions` and `trades` byte-identical across the delete
- `GET /api/watchlist` relocated out of `main.py` into the new router with behavior unchanged, confirmed by the pre-existing `tests/test_app.py` assertion still passing
- Full backend suite: 157 passed, `ruff check app/ tests/` clean

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end add a ticker — HTTP POST to SQLite to the live feed's ticker list** - `4493ca9` (feat)
2. **Task 2: Idempotent remove, the watchlist cap, and the full backend WATCH suite**
   - RED: `3fface5` (test) — failing tests for `remove_ticker` and the DELETE route, confirmed via collection error before implementation existed
   - GREEN: `8f9c885` (feat) — `remove_ticker`, the DELETE route, and a test-bug fix (see Deviations)

**Plan metadata:** commit to follow this summary

## Files Created/Modified
- `backend/app/watchlist/models.py` - `WatchlistRejected` base + `InvalidTickerError`, `DuplicateTickerError`, `WatchlistFullError`
- `backend/app/watchlist/service.py` - `normalize_ticker`, `add_ticker`, `remove_ticker`, `MAX_WATCHLIST_TICKERS`
- `backend/app/watchlist/routes.py` - `create_watchlist_router(cache)` owning GET/POST/DELETE for `/api/watchlist`
- `backend/app/watchlist/__init__.py` - package exports
- `backend/app/main.py` - relocated GET handler removed; `create_watchlist_router(cache)` wired in above the static mount
- `backend/tests/watchlist/test_service.py` - service-level coverage (add/remove, cap, duplicate, invalid)
- `backend/tests/watchlist/test_routes.py` - route-level coverage (add, duplicate, invalid, delete x3, positions/trades isolation)

## Decisions Made
- Relocating `GET /api/watchlist` into the new router (an assumption flagged in the plan itself) — kept, since `tests/test_app.py`'s existing GET assertion passed unchanged, confirming behavior preservation
- Route-level `ticker.strip().upper()` in the DELETE handler's response body duplicates `normalize_ticker`'s normalization for the echoed `ticker` field, since `remove_ticker`'s contract is `-> bool` per the plan's artifact spec, not a tuple

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a test bug in the watchlist-cap test**
- **Found during:** Task 2 (writing the failing `test_add_past_cap_raises_and_writes_nothing` test, then running it after implementation)
- **Issue:** The test generated synthetic cap-filler tickers as `f"T{i}"` (e.g. `T0`, `T1`, ... `T49`), which contain digits and fail `normalize_ticker`'s `^[A-Z]{1,10}$` pattern — the test itself was invalid, not the implementation
- **Fix:** Generate letters-only two-character tickers (`AA`, `AB`, ... spanning the alphabet) for the 50 cap-filler rows
- **Files modified:** `backend/tests/watchlist/test_service.py`
- **Verification:** `pytest tests/watchlist/ -q` — 18 passed after the fix
- **Committed in:** `8f9c885` (part of the Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test authoring, not implementation)
**Impact on plan:** No scope creep; the fix was strictly within the test file the plan asked this task to write.

## Issues Encountered
None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The backend `/api/watchlist` surface (GET/POST/DELETE) is complete and pinned by 18 watchlist-specific tests plus the full 157-test backend suite. Plan 02 can build the frontend add form, sparkline accumulator, and remove control against this exact API contract with no backend changes expected. `WatchlistRejected`'s `code`/`detail()` shape is ready for Plan 02's client-side error messaging and for Phase 4's chat-driven watchlist management to call `add_ticker`/`remove_ticker` directly.

---
*Phase: 03-visual-terminal-watchlist-control*
*Completed: 2026-08-17*
