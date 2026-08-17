---
phase: 03-visual-terminal-watchlist-control
plan: 03
subsystem: full-stack
tags: [fastapi, sqlite, recharts, portfolio-snapshots, background-task, nextjs]

requires:
  - phase: 03-visual-terminal-watchlist-control
    plan: "01"
    provides: "app.watchlist package and routing conventions this plan's SnapshotWriter placement decision (portfolio, not market) mirrors"
  - phase: 02-trading-portfolio
    provides: "execute_trade's open BEGIN IMMEDIATE transaction, get_portfolio's valuation loop, and the HTTP-agnostic service-function contract this plan's snapshot write shares"
provides:
  - "backend/app/portfolio/service.py: record_portfolio_snapshot(), get_portfolio_history(), SNAPSHOT_HISTORY_LIMIT, plus private _positions_value()/_insert_snapshot() — a snapshot INSERT sharing execute_trade's transaction"
  - "GET /api/portfolio/history — chronological snapshot list, empty array on a fresh database"
  - "backend/app/portfolio/snapshot_feed.py: SnapshotWriter, SNAPSHOT_INTERVAL_SECONDS=30.0 — background task mirroring MarketFeed's lifecycle, wired into the FastAPI lifespan"
  - "frontend/lib/types.ts: PortfolioSnapshotPoint; frontend/lib/portfolio.ts: STARTING_CASH_BALANCE=10000"
  - "frontend/components/PnlChart.tsx: Recharts LineChart with loading/empty/single-point/populated states"
  - "recharts@3.10.1 (exact pin) — the only new npm dependency in Phase 3"
affects: ["03-05 (final grid layout repositions the PnlChart mount point)"]

actuals:
  tokens: 7091
  tasks: 2
  commits: 2

tech-stack:
  added: ["recharts@3.10.1"]
  patterns:
    - "Snapshot write shares execute_trade's open BEGIN IMMEDIATE transaction rather than a second call site in the route layer, so every current and future caller (including Phase 4's chat-initiated trades) produces a snapshot automatically"
    - "SnapshotWriter mirrors MarketFeed's start/stop guard, asyncio.create_task loop, and log-don't-raise failure containment, but sleeps before its first tick (MarketFeed ticks first) so the P&L chart's empty-state copy ('within 30 seconds') stays true"
    - "get_portfolio_history selects newest-first with a rowid tie-break, then reverses to ascending order in Python — keeps same-instant snapshots (interval writer + a trade) in stable, deterministic order"

key-files:
  created:
    - backend/app/portfolio/snapshot_feed.py
    - backend/tests/portfolio/test_snapshot_feed.py
    - frontend/components/PnlChart.tsx
  modified:
    - backend/app/portfolio/service.py
    - backend/app/portfolio/routes.py
    - backend/app/portfolio/__init__.py
    - backend/app/main.py
    - backend/tests/portfolio/test_service.py
    - backend/tests/portfolio/test_routes.py
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/lib/types.ts
    - frontend/lib/portfolio.ts
    - frontend/app/page.tsx

key-decisions:
  - "Snapshot write lives inside execute_trade itself, not the HTTP route handler — the module docstring already promises Phase 4's chat flow will call execute_trade directly, bypassing the route, so a route-layer write would silently skip chat-initiated trades"
  - "SnapshotWriter placed at backend/app/portfolio/snapshot_feed.py, not backend/app/market/ as 03-RESEARCH.md's recommended structure suggested — a portfolio-value snapshot is money, and the market package must not depend on the portfolio package"
  - "recharts pinned to an exact version (3.10.1, no caret) in package.json, matching the plan's explicit instruction and 03-RESEARCH.md's Package Legitimacy Audit verdict"

patterns-established:
  - "PnlChart's four-state contract (null=loading skeleton, empty array=empty-state copy, single point=dot-enabled line, 2+=full populated chart) is the template Plan 04's main chart is expected to follow for its own Recharts instance"

requirements-completed: [PORT-09]

coverage:
  - id: D1
    description: "Executing a trade writes exactly one portfolio_snapshots row inside the same transaction as the trade, valuing every open position at current cached prices, not just the traded ticker"
    requirement: PORT-09
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::TestTradeSnapshots (3 assertions: exactly-one-row, prices-every-position, rejected-trade-writes-nothing)"
        status: pass
      - kind: integration
        ref: "manual smoke test — fresh temp DB, TestClient buy, verified total_value == cash_balance + positions_value == 10000.0 exactly"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /api/portfolio/history returns snapshots chronologically, ordered by recorded_at with a rowid tie-break, empty list on a fresh database"
    requirement: PORT-09
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::TestGetPortfolioHistory (3 assertions: fresh-empty, ascending-after-interleaved-trades, identical-timestamp-stable-order)"
        status: pass
      - kind: integration
        ref: "backend/tests/portfolio/test_routes.py::TestGetPortfolioHistory (2 assertions: fresh-200-empty-array, post-trade-200-length-one)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A background task records one snapshot every 30 seconds for as long as the app runs, starts/stops with the lifespan alongside MarketFeed, and survives a failed write without dying"
    requirement: PORT-09
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_snapshot_feed.py::TestSnapshotWriterLifecycle (5 assertions: records-at-least-twice, sleeps-before-first-tick, start-twice-raises, stop-idempotent, raising-recorder-does-not-stop-loop)"
        status: pass
      - kind: integration
        ref: "backend/tests/portfolio/test_snapshot_feed.py::TestRecordPortfolioSnapshotIntegration + manual lifespan smoke test (TestClient enter/exit, 0 pending-task warnings)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The P&L chart renders loading, empty, single-point, and populated states correctly, plotting only recorded snapshots with no synthesized baseline or interpolation"
    requirement: PORT-09
    verification:
      - kind: automated
        ref: "cd frontend && npm test && npm run lint && npx next build --webpack — all exit 0"
        status: pass
      - kind: manual
        ref: "Task 1 human-check (browser verification of empty/populated/reload states) — deferred to phase UAT per the auto-mode tracer-gate precedent set in 03-01/03-02"
        status: deferred
    human_judgment: true

duration: ~40min
completed: 2026-08-17
status: complete
---

# Phase 3 Plan 03: Portfolio Value History & P&L Chart Summary

**Every trade now writes a `portfolio_snapshots` row inside its own transaction, a 30-second background task writes one independently of any open browser tab, `GET /api/portfolio/history` serves them chronologically, and a Recharts `PnlChart` plots the series with working loading/empty/single-point/populated states.**

## Performance

- **Duration:** ~40 min (measured from prior wave base `4608d6e` to final task commit `552bb80`)
- **Tasks:** 2 completed
- **Commits:** 2 (both `feat`)
- **Files touched:** 15 (3 created, 12 modified)

## Accomplishments

- `execute_trade` now computes `total_value = new_cash_balance + _positions_value(conn, cache)` and writes one `portfolio_snapshots` row inside the same `BEGIN IMMEDIATE`/`COMMIT` block as the trade — a rolled-back trade leaves no orphan snapshot, and every current/future caller (including Phase 4's chat flow) gets a snapshot automatically since the write lives in the service function, not the route
- `_positions_value` reprices **every** open position at current cache prices (not just the traded ticker), proven by a two-ticker test where only one ticker was traded
- `get_portfolio_history()` returns snapshots ascending by `recorded_at` with a `rowid` tie-break for same-instant snapshots; `GET /api/portfolio/history` serves it, bounded to `SNAPSHOT_HISTORY_LIMIT = 1000`
- `SnapshotWriter` (`backend/app/portfolio/snapshot_feed.py`) mirrors `MarketFeed`'s start/stop guard and failure containment exactly, but sleeps the interval *before* its first tick so the P&L chart's "within 30 seconds" empty-state copy stays accurate; wired into the FastAPI lifespan beside `MarketFeed`
- `recharts@3.10.1` installed with an exact pin (no caret) and lockfile committed; `PnlChart.tsx` renders a `Skeleton` while loading, the UI-SPEC's exact empty-state copy on zero snapshots, a dot-enabled single point for exactly one snapshot, and a full `LineChart` stroked `--up`/`--down` against the `$10,000` `STARTING_CASH_BALANCE` baseline otherwise
- `page.tsx` fetches history on mount and refetches it on every trade alongside the portfolio, via a new `handleTraded` wrapper passed to `TradeBar`
- End-to-end smoke test (fresh temp SQLite DB, real `TestClient`, real simulator feed): empty history → buy → history returns exactly one row with `total_value == 10000.0` (cash `9809.97` + `1 × 190.03`) and `recorded_at` matching the trade's `executed_at` — confirms the whole write-then-read path, not just the unit tests in isolation
- Full backend suite: 172 passed (was 166 before this plan), `ruff check app/ tests/` clean
- Full frontend suite: 80 passed (unchanged — no new unit tests added for `PnlChart` itself; UI-SPEC/acceptance criteria coverage is via the automated build/lint/test gate plus the deferred manual check), `npm run lint` clean, `npx next build --webpack` succeeds

## Task Commits

Each task was committed atomically:

1. **Task 1: A trade records a snapshot and the P&L chart draws it** — `1866c40` (feat)
2. **Task 2: The 30-second background snapshot writer** — `552bb80` (feat)

**Plan metadata:** this summary commit follows.

## Files Created/Modified

- `backend/app/portfolio/service.py` — `SNAPSHOT_HISTORY_LIMIT`, `record_portfolio_snapshot()`, `get_portfolio_history()`, `_positions_value()`, `_insert_snapshot()`; snapshot write added inside `execute_trade`'s transaction
- `backend/app/portfolio/routes.py` — `GET /api/portfolio/history`
- `backend/app/portfolio/__init__.py` — exports for `record_portfolio_snapshot`, `get_portfolio_history`, `SnapshotWriter`, `SNAPSHOT_INTERVAL_SECONDS`
- `backend/app/portfolio/snapshot_feed.py` — `SnapshotWriter`, `SNAPSHOT_INTERVAL_SECONDS = 30.0`
- `backend/app/main.py` — `SnapshotWriter(cache)` constructed, started, and stopped in the lifespan beside `MarketFeed`
- `backend/tests/portfolio/test_service.py` — `TestTradeSnapshots`, `TestGetPortfolioHistory`, `TestRecordPortfolioSnapshot` classes (9 new test methods)
- `backend/tests/portfolio/test_routes.py` — `TestGetPortfolioHistory` class (2 new test methods)
- `backend/tests/portfolio/test_snapshot_feed.py` — new file, 6 lifecycle/integration tests
- `frontend/package.json` / `frontend/package-lock.json` — `recharts@3.10.1` added, exact pin
- `frontend/lib/types.ts` — `PortfolioSnapshotPoint`
- `frontend/lib/portfolio.ts` — `STARTING_CASH_BALANCE = 10000`
- `frontend/components/PnlChart.tsx` — new file, the P&L chart component
- `frontend/app/page.tsx` — `portfolioHistory` state, `fetchPortfolioHistory`, `handleTraded` wrapper, `<PnlChart>` mounted beneath the positions table

## Decisions Made

- Snapshot write placed inside `execute_trade` rather than the route handler (Pattern 4 from 03-RESEARCH.md) — the module docstring's promise that Phase 4 will call `execute_trade` directly makes this the only placement that keeps "every trade produces a snapshot" true for every caller
- `SnapshotWriter` module path is `backend/app/portfolio/snapshot_feed.py`, deviating from 03-RESEARCH.md's suggested `backend/app/market/snapshot_feed.py` — the plan's own flagged assumption, which this execution followed exactly, since a portfolio-value writer imports the portfolio service and must not live in the price-only `market` package
- `get_portfolio_history`'s tie-break uses SQLite's implicit `rowid` (the table has no `WITHOUT ROWID` clause) rather than a separate sequence column, avoiding a schema change for a same-instant ordering guarantee

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `frontend/node_modules` did not exist in this fresh worktree**
- **Found during:** Task 1, before running `npm test`
- **Issue:** Each git worktree needs its own `npm install` since `node_modules` is gitignored — same finding as 03-02
- **Fix:** Ran `npm install` in `frontend/` before installing `recharts`
- **Files modified:** none tracked
- **Verification:** subsequent `npm test`/`npm run lint`/`npx next build` all ran cleanly

**2. [Rule 3 - Blocking issue] `npm install recharts@3.10.1` initially failed with a corrupted lockfile entry**
- **Found during:** Task 1, installing the new dependency
- **Issue:** The first `npm install` (bringing in the existing dependency tree fresh in this worktree) produced a malformed `node_modules/@img/sharp-wasm32/node_modules/@emnapi/runtime` entry in `package-lock.json` with no `version`/`resolved` fields — an npm 11.6.2 arborist bug when installing `sharp`'s optional wasm32 binaries. This crashed every subsequent `npm install` (including `recharts`) with `TypeError: Invalid Version` during dedupe
- **Fix:** Reset `package-lock.json` to the git-committed version (`git checkout -- package-lock.json`), removed `node_modules`, ran a clean `npm install` (which this time produced no malformed entry), then `npm install recharts@3.10.1` succeeded
- **Files modified:** none beyond the intended `package.json`/`package-lock.json` recharts addition
- **Verification:** `grep -n "sharp-wasm32/node_modules/@emnapi/runtime"` confirmed no malformed entry in the final lockfile; `npm test`/`npm run lint`/`npx next build --webpack` all passed afterward

---

**Total deviations:** 2 auto-fixed (both environment/tooling, not implementation bugs)
**Impact on plan:** No scope creep; both fixes were environment setup steps with no source-code consequence, matching the pattern already documented in 03-02's summary.

## Issues Encountered

None beyond the two environment-setup deviations above.

## User Setup Required

None — no external service configuration required. Same environment note as 03-01/03-02 applies: a fresh worktree needs `npm install` in `frontend/` before tests/lint/build will run.

## Next Phase Readiness

`GET /api/portfolio/history`, `record_portfolio_snapshot`, and `PnlChart`'s `PortfolioSnapshotPoint[] | null` prop contract are stable for Plan 05's final grid layout, which only repositions the chart's mount point — no interface changes expected. `PnlChart`'s four-state pattern (loading/empty/single-point/populated) is the template Plan 04's main chart should follow for its own Recharts instance. Task 1's human-check (browser verification of the P&L chart's empty→populated→reload-persists flow) was not run against a live `uvicorn` server serving the static export in this execution — automated verify (tests/lint/build) is clean and a direct `TestClient`-based end-to-end smoke test confirmed the write/read path, but the visual browser check is flagged as deferred to phase UAT, matching 03-02's precedent.

## Known Stubs

None — no hardcoded empty values or placeholder text were introduced. `PnlChart` renders only real data returned by `GET /api/portfolio/history`; no synthesized baseline point, no interpolation, no mock data path.

## Threat Flags

None — both new surfaces (`GET /api/portfolio/history` and `npm install recharts@3.10.1`) were already registered and dispositioned in this plan's own `<threat_model>` (T-03-06 through T-03-10, T-03-SC-02), with no additional surface introduced beyond what was planned.

---
*Phase: 03-visual-terminal-watchlist-control*
*Completed: 2026-08-17*
