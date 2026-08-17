---
phase: 03-visual-terminal-watchlist-control
verified: 2026-08-17T14:45:00Z
status: human_needed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "POST a new ticker (e.g. PYPL) via the live add form and wait ~2s"
    expected: "Row appears immediately with an em-dash/null price, then shows a live streaming price within one poll interval; posting the same ticker again shows the duplicate error inline"
    why_human: "Visual rendering and timing of the live price transition in a real browser; automated evidence only covers the HTTP contract and unit-level logic"
  - test: "Type an invalid ticker (e.g. aa1) into the add form"
    expected: "Add button stays disabled and no request is sent"
    why_human: "Client-side form interaction state, not exercised by a DOM-rendering test"
  - test: "Click the remove (x) control on a watchlist row, then re-add the same ticker"
    expected: "Row disappears immediately; re-adding starts its sparkline empty rather than resuming its old shape; portfolio/cash/positions unaffected by a watchlist removal"
    why_human: "Visual sparkline reset and row removal are DOM/browser behaviors outside static analysis"
  - test: "Load the app against a fresh database and watch the Portfolio Value panel without trading"
    expected: "Empty state, then a chart appears with a new point roughly every 30 seconds"
    why_human: "Real-time timing behavior in a live browser session"
  - test: "Buy shares, confirm the P&L chart gets an immediate point, buy again later and confirm two points join into a line, reload and confirm both persist"
    expected: "Chart updates immediately on trade and on the 30s cadence, survives reload"
    why_human: "Visual chart rendering across a page reload"
  - test: "Buy a large position and two smaller ones; observe the heatmap"
    expected: "Rectangle sizes are visibly proportional to position weight; losing positions render red, winning ones green, each with a signed percent label"
    why_human: "Visual color/size perception in a rendered browser, not verifiable via grep/unit test"
  - test: "Click AAPL then GOOGL rows in the watchlist; click the remove control on a row"
    expected: "Main chart switches instantly with no loading flicker on ticker click; remove control does not also select/switch the chart"
    why_human: "Click-interaction and render-timing behavior in a live DOM"
  - test: "Confirm the AI Copilot placeholder panel visually matches the height/chrome of the heatmap and P&L chart"
    expected: "Same panel treatment, no interactive elements"
    why_human: "Visual chrome parity is a rendering check"
  - test: "Open the app maximized on a wide screen, then narrow to ~800px, then widen back"
    expected: "All eight panels visible without horizontal scroll at wide width; single stacked column with nothing hidden at ~800px; charts redraw (not blank) at both widths; removing all watchlist tickers doesn't shift the rest of the layout"
    why_human: "Responsive layout behavior across viewport widths requires a real browser"
  - test: "Full desktop layout — watchlist column padding/alignment, no clipping in any of the five row columns"
    expected: "Ticker, price, percent, sparkline, and remove control all render without clipping at the 420px column width"
    why_human: "Visual pixel-level rendering check"
---

# Phase 3: Visual Terminal & Watchlist Control Verification Report

**Phase Goal:** A user can see the whole portfolio at a glance and curate which tickers the terminal tracks
**Verified:** 2026-08-17T14:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User sees a portfolio heatmap where each position is a rectangle sized by its share of the portfolio and colored green for profit or red for loss | ✓ VERIFIED | `frontend/lib/heatmap.ts::deriveHeatmapItems` weights by `quantity*price / total` (excludes unpriced positions, sums to 1); `HeatmapCell.tsx` sets `flexGrow: weight` and colors `bg-up/70`/`bg-down/70` from `pnlPercent >= 0`, where `pnlPercent` is `PositionRowData.changePercent` — computed in `frontend/lib/portfolio.ts::derivePositionRows` as `(price - avg_cost)/avg_cost*100`, i.e. unrealized P&L, not daily price change. 15/15 unit tests pass (`heatmap.test.ts`). Wired in `page.tsx`: `heatmapItems = useMemo(() => deriveHeatmapItems(positionRows), ...)` → `<Heatmap items={heatmapItems} />`. |
| 2 | User sees a P&L chart of total portfolio value over time that gains a new point every 30 seconds and immediately after each trade | ✓ VERIFIED | Backend: `execute_trade` writes a `portfolio_snapshots` row inside its own `BEGIN IMMEDIATE` transaction (`backend/app/portfolio/service.py`); `SnapshotWriter` (`snapshot_feed.py`, `SNAPSHOT_INTERVAL_SECONDS = 30.0`) is started in the FastAPI lifespan beside `MarketFeed`. Confirmed by 24 passing backend tests including `TestSnapshotWriterLifecycle` (records at least twice over intervals, sleeps before first tick) and `TestTradeSnapshots`. **Live smoke test performed during this verification**: fresh DB → `GET /api/portfolio/history` returned `[]` → executed a real buy trade via `TestClient`-equivalent live server → `GET /api/portfolio/history` immediately returned one row with `total_value` matching cash+positions. `frontend/components/PnlChart.tsx` renders the real `GET /api/portfolio/history` response with loading/empty/single-point/populated states, no synthesized data. |
| 3 | Each watchlist row grows a sparkline that fills in progressively from the live stream after page load | ✓ VERIFIED | `frontend/lib/priceHistory.ts::appendTicks` accumulates timestamp-discriminated points per ticker from the single existing SSE `usePriceStream()`, capped at `MAX_HISTORY_POINTS=300`; `usePriceHistory.ts` binds it to the page's one live connection (no second `EventSource`). `Sparkline.tsx` renders a hand-rolled inline SVG polyline from these points. `WatchlistRow.tsx` passes `points={history[entry.ticker] ?? []}`. 10/10 `priceHistory.test.ts` assertions pass, including that a removed-then-re-added ticker starts empty (`pruneToWatchlist`). |
| 4 | User can add and remove watchlist tickers; added tickers begin streaming prices, removed ones disappear from the grid | ✓ VERIFIED | Full-stack, both directions confirmed. Backend: `POST /api/watchlist` (validates via `normalize_ticker`, `INSERT OR ABORT`, `UNIQUE(user_id,ticker)` as the sole duplicate arbiter) and `DELETE /api/watchlist/{ticker}` (idempotent, isolated from `positions`/`trades` — asserted by a dedicated test comparing table contents before/after). **Live smoke test performed during this verification** against a running uvicorn instance: `POST {"ticker":"pypl"}` → returned entry with null price fields → after ~1.5s, `GET /api/watchlist` showed PYPL with a live price (`direction: "up"`, non-null price) — proving the running `MarketFeed` picked it up with no restart (`MarketFeed._tick()` re-reads `db.watchlist_tickers()` every poll). Duplicate POST returned `400` with `duplicate_ticker` code. `DELETE` twice returned `removed: true` then `removed: false`, both `200`. 24 backend watchlist/route tests pass. Frontend: `page.tsx`'s `handleAdded`/`handleRemove` wire `WatchlistAddForm`/`WatchlistRow`'s remove control to these endpoints; `Watchlist.tsx` performs non-optimistic removal (row only disappears on confirmed success). |
| 5 | Clicking a watchlist row loads that ticker into the main chart area, and the full layout — watchlist, main chart, heatmap, P&L chart, positions table, trade bar, chat panel, header — fits a wide desktop screen without excess scrolling and stays usable at tablet width | ✓ VERIFIED | `MainChart.tsx` renders `selectedTicker`'s already-accumulated `history[ticker]` with zero `fetch`/`EventSource` calls (grep-confirmed 0 matches) — instant switch on click, no loading state. `page.tsx` mounts all eight panels in the declared order: `Header`, disclaimer, `TradeBar`, `Watchlist` (fixed `lg:w-[420px] lg:shrink-0`), `MainChart`, a `grid grid-cols-1 lg:grid-cols-2` sub-grid holding `Heatmap`+`PnlChart`, `PositionsTable`, `ChatPlaceholder`. The two-column region is `flex flex-col lg:flex-row` — column-stacked below the `lg` (1024px) breakpoint by structural default, not a conditional/hidden branch; `grep -c hidden frontend/app/page.tsx` returns 0, so nothing is hidden at any width. |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/watchlist/{__init__,models,service,routes}.py` | WATCH-02/03 backend surface | ✓ VERIFIED | Exists, substantive, wired into `main.py` above the static mount; 24 tests pass; live smoke-tested |
| `backend/app/portfolio/snapshot_feed.py` | 30s background snapshot writer | ✓ VERIFIED | `SnapshotWriter` class, wired into lifespan, 6 lifecycle/integration tests pass |
| `backend/app/portfolio/service.py` (extended) | `record_portfolio_snapshot`, `get_portfolio_history` | ✓ VERIFIED | Real SQL, snapshot write inside `execute_trade`'s transaction, live-smoke-tested |
| `frontend/lib/priceHistory.ts`, `usePriceHistory.ts` | Sparkline/main-chart history accumulator | ✓ VERIFIED | Pure, tested (10 assertions), wired into `Watchlist`/`MainChart` |
| `frontend/lib/heatmap.ts` | Weight derivation + squarify layout | ✓ VERIFIED | Pure, tested (15 assertions), wired into `Heatmap`/`HeatmapCell` |
| `frontend/lib/watchlistForm.ts` | Client-side validation + error mapping | ✓ VERIFIED | Tested (10 assertions), wired into `WatchlistAddForm` |
| `frontend/components/{Sparkline,WatchlistAddForm,Heatmap,HeatmapCell,MainChart,PnlChart,ChatPlaceholder}.tsx` | Visual panels | ✓ VERIFIED | All exist, non-stub, real data props, no debt markers |
| `frontend/app/page.tsx` | Final eight-panel grid | ✓ VERIFIED | All panels mounted, real state/data flow, responsive structure |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `backend/app/main.py` | `backend/app/watchlist/routes.py` | `create_watchlist_router(cache)` registered above static mount | ✓ WIRED | Confirmed by grep + live server routing |
| `backend/app/watchlist/service.py` | `backend/app/db/database.py` | `connect()` + `?`-bound INSERT/DELETE | ✓ WIRED | No string interpolation found (grepped); live-tested |
| `backend/app/market/feed.py` | `backend/app/watchlist` table | `_tick()` re-reads `db.watchlist_tickers()` every poll | ✓ WIRED | Live smoke test: added ticker got a live price within ~1.5s with no server restart |
| `backend/app/portfolio/service.py::execute_trade` | `portfolio_snapshots` table | Shared `BEGIN IMMEDIATE` transaction | ✓ WIRED | Live smoke test: buy → history immediately non-empty |
| `frontend/lib/usePriceStream` | `frontend/lib/usePriceHistory` | Single shared SSE connection, no second `EventSource` | ✓ WIRED | Grepped: `MainChart.tsx`/`Sparkline.tsx` make zero fetch/EventSource calls |
| `frontend/lib/portfolio.ts::derivePositionRows` | `frontend/lib/heatmap.ts::deriveHeatmapItems` | `positionRows` memo feeds `heatmapItems` memo | ✓ WIRED | Confirmed in `page.tsx`; `pnlPercent` correctly sources unrealized P&L, not daily price change |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `HeatmapCell` | `weight`, `pnlPercent` | `GET /api/portfolio` → `derivePositionRows` → `deriveHeatmapItems` | Yes | ✓ FLOWING |
| `PnlChart` | `points` | `GET /api/portfolio/history` | Yes | ✓ FLOWING |
| `Sparkline` | `points` | SSE `usePriceStream` → `usePriceHistory` accumulator | Yes | ✓ FLOWING |
| `MainChart` | `points`, `price`, `changePercent` | Same accumulator + live `prices` map, keyed by `selectedTicker` | Yes | ✓ FLOWING |
| `Watchlist` rows | `price`, `changePercent`, `direction` | SSE `prices` map with fallback to initial `GET /api/watchlist` fetch | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend full suite | `cd backend && uv run --extra dev pytest -q` | 172 passed | ✓ PASS |
| Backend lint | `cd backend && uv run ruff check app/ tests/` | All checks passed | ✓ PASS |
| Frontend full suite | `cd frontend && npm test -- --run` | 95 passed (8 files) | ✓ PASS |
| Frontend lint | `cd frontend && npm run lint` | Clean | ✓ PASS |
| Frontend production build | `cd frontend && npx next build --webpack` | Compiled successfully, static export generated | ✓ PASS |
| Watchlist add → live feed pickup | Live uvicorn: `POST /api/watchlist {"ticker":"pypl"}` then `GET /api/watchlist` after 1.5s | Null price fields immediately, live price (`direction: up`) after one poll | ✓ PASS |
| Duplicate ticker rejected | Live: repeat POST for PYPL | `400`, `{"code":"duplicate_ticker",...}` | ✓ PASS |
| Idempotent delete | Live: `DELETE /api/watchlist/PYPL` twice | `removed: true` then `removed: false`, both `200` | ✓ PASS |
| Trade → immediate snapshot | Live: `GET /api/portfolio/history` (empty) → buy trade → `GET /api/portfolio/history` | `[]` → one row with correct `total_value` | ✓ PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` convention; verification used the project's standard pytest/vitest/build gates plus a live end-to-end smoke test against a real uvicorn instance (see Behavioral Spot-Checks above).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PORT-08 | 03-04 | Portfolio heatmap (treemap) sized by weight, colored by P&L | ✓ SATISFIED | `heatmap.ts`, `HeatmapCell.tsx`, 15 tests, wired |
| PORT-09 | 03-03 | P&L chart of total portfolio value over time, every 30s + after trade | ✓ SATISFIED | `SnapshotWriter`, `execute_trade` snapshot write, `PnlChart.tsx`, live-smoke-tested |
| WATCH-02 | 03-01, 03-02 | Add a ticker to the watchlist | ✓ SATISFIED | Full-stack, live-smoke-tested |
| WATCH-03 | 03-01, 03-02 | Remove a ticker from the watchlist | ✓ SATISFIED | Full-stack, idempotent, isolated, live-smoke-tested |
| WATCH-04 | 03-02 | Sparkline mini-chart accumulated from SSE since page load | ✓ SATISFIED | `priceHistory.ts`, `Sparkline.tsx`, 10 tests |
| WATCH-05 | 03-04 | Clicking a watchlist ticker selects it in the main chart | ✓ SATISFIED | `MainChart.tsx`, no fetch, wired to `selectedTicker` |
| UI-02 | 03-05 | All eight panels visible on wide desktop without excess scrolling | ✓ SATISFIED | `page.tsx` final grid, all panels mounted, no explicit height overrides |
| UI-04 | 03-05 | Usable at tablet width | ✓ SATISFIED | Structural `flex-col`/`lg:flex-row`, zero `hidden` classes |
| TEST-03 | 03-02, 03-04 | Frontend unit tests cover price flash animation, watchlist CRUD, and portfolio display calculations | ⚠️ SATISFIED (partial, by established convention) | `watchlistForm.test.ts`/`priceHistory.test.ts`/`heatmap.test.ts` cover client-side validation, history accumulation/pruning, and heatmap derivation (all pure-function tests, matching the project's pre-existing Phase 1/2 pure-function-only testing convention documented in `03-RESEARCH.md`). No test exercises the actual `fetch`-based add/remove network call in `Watchlist.tsx`/`page.tsx` (`handleAdded`/`handleRemove`) — this is thinner than a literal reading of "watchlist CRUD" would suggest, though consistent with how this repo has satisfied equivalent TEST requirements in prior phases. Both plans explicitly flagged this as "(TEST-03, partial)" in their own text. |

No orphaned requirements — all 9 phase-declared IDs (PORT-08, PORT-09, WATCH-02..05, UI-02, UI-04, TEST-03) are covered by at least one plan.

### Anti-Patterns Found

No debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder text) found in any file modified by this phase.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/app/page.tsx` | `handleRemove` (~108-122) | Unresolved code-review finding WR-03: removing the *currently selected* watchlist ticker never clears `selectedTicker`. The row correctly disappears from the grid (criterion 4 holds), but `MainChart`'s header (`selectedPrice`/`selectedChangePercent`, read from the never-pruned `prices` map) keeps showing a frozen, no-longer-live price for the removed ticker, while the chart body below switches to "select a ticker." | ⚠️ Warning | Not a blocker against any of the 5 stated success criteria, but a real, previously-identified (03-REVIEW.md WR-03) UX/data-staleness bug in the remove flow, unresolved as of this verification. |
| `backend/app/watchlist/service.py` | `add_ticker` (~43-59) | 03-REVIEW.md WR-01: cap check and insert are not wrapped in one transaction (unlike `execute_trade`'s `BEGIN IMMEDIATE`), so two concurrent adds could both pass the 50-ticker cap check. | ℹ️ Info | Single-user, loopback, zero-auth app — low real-world impact; documented in 03-REVIEW.md, not re-litigated here. |

### Human Verification Required

10 items harvested from every plan's deferred `<human-check>` verify blocks (all five plans in this phase explicitly deferred their human-check to end-of-phase UAT rather than running them mid-execution). See YAML frontmatter `human_verification` for the full structured list. Summary:

1. **Live add-form flow** — type/post a ticker, watch the row appear with null→live price and a growing sparkline in a real browser.
2. **Invalid-ticker form guard** — Add button stays disabled for a malformed symbol.
3. **Remove-then-re-add sparkline reset** — visual confirmation the sparkline starts empty, not resumed.
4. **P&L chart 30-second cadence** — visual confirmation of a new point appearing roughly every 30s with no trading.
5. **P&L chart trade-triggered point + reload persistence** — visual confirmation across a page reload.
6. **Heatmap proportional sizing and color** — visual confirmation rectangle sizes and red/green coloring are correct and legible.
7. **Main chart click-to-select, no flicker, remove-control isolation** — click interaction in a live DOM.
8. **Chat placeholder visual chrome parity** — height/border match with Heatmap/PnlChart.
9. **Responsive layout at wide and ~800px widths** — no horizontal scroll, no hidden panels, charts redraw on resize, empty-watchlist stability.
10. **Watchlist column alignment/no-clipping at 420px width** — pixel-level rendering check.

### Gaps Summary

No blocking gaps. All 5 phase-goal observable truths and all 9 declared requirements (PORT-08, PORT-09, WATCH-02 through WATCH-05, UI-02, UI-04, TEST-03) are backed by passing automated tests, a clean production build, and a live end-to-end smoke test performed during this verification against a running uvicorn instance (watchlist add/remove/duplicate/idempotent-delete, and trade-triggered portfolio snapshot). TEST-03 is satisfied only in the narrower, pure-function sense the project has consistently used since Phase 1 — no test exercises the live network add/remove path itself — noted above but not treated as a blocker since it matches established, already-accepted repo convention. One previously-documented, unresolved code-review warning (WR-03: stale main-chart header after removing the selected ticker) is noted but does not violate any of the 5 stated success criteria. Status is `human_needed` because every plan in this phase explicitly deferred its visual/interactive human-check to end-of-phase UAT — none of those 10 checks were run in a real browser as part of this verification.

---

_Verified: 2026-08-17T14:45:00Z_
_Verifier: Claude (gsd-verifier)_
