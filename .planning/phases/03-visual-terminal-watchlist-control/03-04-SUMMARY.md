---
phase: 03-visual-terminal-watchlist-control
plan: 04
subsystem: frontend
tags: [nextjs, react, vitest, recharts, treemap, squarify, heatmap]

requires:
  - phase: 03-visual-terminal-watchlist-control
    plan: "02"
    provides: "usePriceHistory()/PricePoint accumulator this plan's MainChart consumes directly, and derivePositionRows's positionRows memo this plan's heatmap re-derives from"
  - phase: 03-visual-terminal-watchlist-control
    plan: "03"
    provides: "PnlChart.tsx's four-state Recharts convention (loading/empty/single-point/populated) this plan's MainChart mirrors for its own chart instance"
provides:
  - "frontend/lib/heatmap.ts: HeatmapItem, HeatmapRow, HEATMAP_LABEL_MIN_WEIGHT, deriveHeatmapItems(), squarify() — pure position-weight derivation and squarified row layout, no framework import, no pixel math"
  - "frontend/components/Heatmap.tsx / HeatmapCell.tsx: nested flexbox treemap panel, one flex-grow-sized P&L-coloured rectangle per position"
  - "frontend/components/MainChart.tsx: Recharts LineChart of the selected watchlist ticker's accumulated price history, accent-blue stroke, no fetch"
affects: ["03-05 (final grid layout repositions the Heatmap, MainChart, and PnlChart mount points into the desktop grid)"]

actuals:
  tokens: 4950
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Pure derivation/component split (heatmap.ts / Heatmap.tsx+HeatmapCell.tsx) mirroring priceHistory.ts / usePriceHistory.ts and portfolio.ts / PositionsTable.tsx"
    - "Squarified treemap laid out entirely via nested flexbox flex-grow — no element measurement, no ResizeObserver, matching D-02's hand-built-not-library decision"
    - "MainChart follows PnlChart's exact four-state Recharts contract (loading n/a here since no fetch; empty-prompt/single-point-dot/populated), reusing the same CSS-variable-as-stroke-string convention"

key-files:
  created:
    - frontend/lib/heatmap.ts
    - frontend/lib/heatmap.test.ts
    - frontend/components/Heatmap.tsx
    - frontend/components/HeatmapCell.tsx
    - frontend/components/MainChart.tsx
  modified:
    - frontend/app/page.tsx

key-decisions:
  - "squarify's worst-ratio side parameter is computed once from containerAspect and held fixed across all rows rather than shrinking per row (as a full pixel-placement squarify would) — the module has no real container dimensions to shrink against since layout is delegated entirely to flexbox; RESEARCH.md Assumption A1 explicitly accepts this produces a correctly weight-proportional partition with possibly less-square rectangles, which is what the unit tests assert"
  - "MainChart shows the same select-a-ticker prompt both when no ticker is selected and when a selected ticker has zero accumulated points, via one shared showPrompt boolean and one string constant — satisfies the plan's own acceptance criterion that the prompt string appear exactly once in the file while still covering both UI-SPEC states"
  - "selectedPoints/selectedPrice/selectedChangePercent in page.tsx were placed after the usePriceHistory() call (not before) to avoid a temporal-dead-zone reference to the history const — caught by npx next build's TypeScript check during Task 2 verification before commit"

patterns-established:
  - "heatmap.ts's flexGrow-only sizing contract (component computes no pixels, reads no bounding rectangle, registers no resize observer) is the template any future treemap-shaped visualization in this app should follow"

requirements-completed: [PORT-08, WATCH-05]

coverage:
  - id: D1
    description: "The portfolio heatmap renders one rectangle per open position, sized by that position's share of total portfolio value and filled green for a profitable position or red for a losing one"
    requirement: PORT-08
    verification:
      - kind: unit
        ref: "frontend/lib/heatmap.test.ts (15 assertions: null/empty/one/two/ten positions, null-price exclusion, all-null-price empty result, changePercent passthrough, descending sort, squarify partition/weight-sum/order/no-mutate)"
        status: pass
      - kind: automated
        ref: "cd frontend && npx vitest run lib/heatmap.test.ts && npm test && npm run lint && npx next build --webpack"
        status: pass
      - kind: manual
        ref: "Task 1 human-check (browser verification of empty/single-position/multi-position heatmap rendering) — deferred to phase UAT per the auto-mode tracer-gate precedent set in 03-01/03-02/03-03"
        status: deferred
    human_judgment: true
  - id: D2
    description: "Every heatmap cell carries a signed percent label alongside its colour so profit/loss is legible without perceiving red against green"
    requirement: PORT-08
    verification:
      - kind: unit
        ref: "grep -c 'formatPercent' frontend/components/HeatmapCell.tsx (non-colour P&L channel present)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Clicking a watchlist row loads that ticker into the main chart, drawn from the price history already accumulated for that ticker since page load, with no fetch and no loading flicker"
    requirement: WATCH-05
    verification:
      - kind: automated
        ref: "grep -Ec 'fetch\\(|EventSource' frontend/components/MainChart.tsx outputs 0; cd frontend && npm test && npm run lint && npx next build --webpack"
        status: pass
      - kind: manual
        ref: "Task 2 human-check (click AAPL/GOOGL rows, confirm instant switch with no loading flicker, confirm remove control does not select) — deferred to phase UAT"
        status: deferred
    human_judgment: true

duration: ~25min
completed: 2026-08-17
status: complete
---

# Phase 3 Plan 04: Portfolio Heatmap & Main Chart Summary

**A pure, unit-tested `heatmap.ts` module derives position weights and a squarified flexbox row layout with no pixel math, rendered as a nested-flexbox treemap where every position is a P&L-coloured, signed-percent-labelled rectangle sized by real portfolio weight; and clicking any watchlist row now draws that ticker's already-accumulated price history into a Recharts main chart with no fetch and no loading flicker.**

## Performance

- **Duration:** ~25 min (measured from prior wave base `753dd07` to final task commit `c82be22`)
- **Tasks:** 2 completed
- **Commits:** 2 (both `feat`)
- **Files touched:** 6 (5 created, 1 modified)

## Accomplishments

- `frontend/lib/heatmap.ts` — pure, framework-free `deriveHeatmapItems()` (values each position as `quantity * price`, drops unpriced positions, normalizes remaining weights to sum to 1, sorts descending, applies no minimum-size floor) and `squarify()` (the Bruls/Huizing/van Wijk row-building heuristic using the paper's worst-aspect-ratio formula, partitioning input into rows with no drops/duplicates and no mutation)
- `frontend/lib/heatmap.test.ts` — 15 assertions pinning both functions' zero/one/many boundary behavior, the null-price exclusion rule, weight-sum-to-1 tolerance, and the squarify partition/weight-sum/order/no-mutate invariants — TEST-03's heatmap half
- `frontend/components/HeatmapCell.tsx` — one `<div>` whose only inline style is `flexGrow: weight`; `bg-up/70`/`bg-down/70` fill by P&L sign; signed percent via `formatPercent` as the non-colour channel; accessible `title` combining ticker, weight%, and P&L%; no raw-HTML injection prop
- `frontend/components/Heatmap.tsx` — three-state panel (null skeleton, empty array reuses `PositionsTable`'s exact "No open positions" copy verbatim, populated renders `squarify()`'s rows as nested flex containers) with an explicit `h-64 min-h-64` container
- `frontend/components/MainChart.tsx` — Recharts `LineChart` stroked `var(--primary)` (never `--up`/`--down` — a selection indicator, not a P&L signal), header line with ticker/live-price/percent, single shared prompt string covering both "no ticker selected" and "ticker selected but zero accumulated points" via one `showPrompt` boolean, dot-enabled rendering for exactly one point
- `frontend/app/page.tsx` — `heatmapItems` derived via `useMemo` over the existing `positionRows` (no second portfolio fetch); `MainChart` fed by the existing `selectedTicker` state and the existing `history`/`prices` maps (no new state, no new event plumbing — WATCH-05's consumer for state that was already wired)
- Full frontend suite: 95 passed (was 80 before this plan, +15 new), `npm run lint` clean, `npx next build --webpack` succeeds (TypeScript check caught and this execution fixed a temporal-dead-zone ordering bug before commit — see Deviations)
- Full backend suite: 172 passed, unchanged (this plan touches no backend file)

## Task Commits

Each task was committed atomically:

1. **Task 1 (TDD): Portfolio heatmap — weights, squarified layout, and the flexbox treemap** — `273df69` (feat)
2. **Task 2: Main chart — clicking a watchlist row draws that ticker** — `c82be22` (feat)

**Plan metadata:** this summary commit follows.

## Files Created/Modified

- `frontend/lib/heatmap.ts` — `HeatmapItem`, `HeatmapRow`, `HEATMAP_LABEL_MIN_WEIGHT`, `deriveHeatmapItems()`, `squarify()`
- `frontend/lib/heatmap.test.ts` — 15 assertions (RED confirmed before implementation: import failure with no `heatmap.ts` present, then GREEN once written)
- `frontend/components/HeatmapCell.tsx` — one weighted, P&L-coloured rectangle
- `frontend/components/Heatmap.tsx` — loading/empty/populated panel
- `frontend/components/MainChart.tsx` — the selected-ticker line chart
- `frontend/app/page.tsx` — `heatmapItems` memo, `<Heatmap>` mount, `selectedPoints`/`selectedPrice`/`selectedChangePercent` derivations, `<MainChart>` mount

## Decisions Made

- `squarify`'s worst-ratio `side` parameter is computed once (from `containerAspect`, default 1) and held fixed across all rows, rather than shrinking the remaining rectangle per row as a full pixel-placement squarify implementation would — there are no real container pixels to shrink against since layout is fully delegated to flexbox `flex-grow`. This matches the plan's own flagged Assumption 4 (RESEARCH.md Assumption A1): the partition stays correctly weight-proportional, which is what the unit tests assert; only the rectangles' exact squareness may deviate from the reference algorithm, which is not tested
- `MainChart`'s prompt copy renders through one shared `showPrompt` boolean (`ticker == null || points.length === 0`) and one string constant, so the literal prompt sentence appears exactly once in the source while still covering both UI-SPEC empty states (no selection, and a just-selected ticker with zero accumulated points)
- Heatmap and MainChart panels were placed inline in the existing single-column `main` stack in `page.tsx` (Watchlist → MainChart → Heatmap → PositionsTable → PnlChart) since the plan explicitly defers the final desktop grid to Plan 05

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Temporal-dead-zone reference to `history` in `page.tsx`**
- **Found during:** Task 2, `npx next build --webpack`'s TypeScript check
- **Issue:** The first draft placed `selectedPoints`/`selectedPrice`/`selectedChangePercent` (which read the `history` and `prices` consts) above the `usePriceHistory()` call that declares `history`, referencing a `const` before its declaration
- **Fix:** Moved the three derivations below the `usePriceHistory()` call
- **Files modified:** `frontend/app/page.tsx`
- **Verification:** `npx next build --webpack`'s TypeScript step passed cleanly afterward; `npm test`/`npm run lint` unaffected

**2. [Rule 3 - Blocking issue] `frontend/node_modules` did not exist in this fresh worktree**
- **Found during:** before Task 1's first test run
- **Issue:** Same finding as 03-02/03-03 — each git worktree needs its own `npm install` since `node_modules` is gitignored
- **Fix:** Ran `npm install` in `frontend/`; reverted the resulting 3-line `package-lock.json` normalization diff (`peer`/`optional` metadata churn, no version changes) since it was incidental to this task
- **Files modified:** none tracked (lockfile diff reverted)
- **Verification:** `npm test`, `npm run lint`, `npx next build` all ran cleanly afterward

**3. [Rule 3 - Blocking issue] `npx next build --webpack` hung under the default sandbox on the font CDN fetch**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** Same root cause documented in 03-02's summary — `next/font/google` fetches from Google's CDN at build time, which is outside the sandbox's network allowlist, so the build hangs rather than failing fast. The first Task 1 build attempt was left running as a background process and had to be killed and its stale `.next/lock` removed before a retry could proceed
- **Fix:** Re-ran the build with the sandbox disabled for that one command; confirmed no code fault
- **Files modified:** none
- **Verification:** `npx next build --webpack` completed successfully both times once network access was available

**4. [Rule 3 - Blocking issue] `uv run --extra dev pytest` failed to initialize its cache under the sandbox**
- **Found during:** full-stack smoke verification (backend suite, unchanged by this plan)
- **Issue:** `uv`'s cache directory access (`~/.cache/uv/.../.git`) was denied under the default sandbox's filesystem restrictions
- **Fix:** Re-ran with the sandbox disabled for that one command; this is a local `uv` cache access need, not a code defect
- **Files modified:** none
- **Verification:** 172 passed, unchanged from the prior plan's baseline

---

**Total deviations:** 1 auto-fixed bug (TDZ ordering, caught before commit by the build's own TypeScript check) + 3 auto-fixed environment/tooling issues (matching the pattern already documented in 03-02/03-03's summaries)
**Impact on plan:** No scope creep. The TDZ fix is a one-line reorder with no behavioral change; the three environment fixes have no source-code consequence.

## Issues Encountered

None beyond the four deviations above, all resolved before the relevant task's commit.

## User Setup Required

None — no external service configuration required. Same environment notes as 03-01/03-02/03-03 apply: a fresh worktree needs `npm install` in `frontend/` before tests/lint/build will run, and a restricted network egress list needs to allow Google's font CDN (or run the build with that restriction lifted) for `next/font/google` to resolve at build time. Additionally noted this plan: `uv run` from `backend/` may need sandbox filesystem restrictions lifted for its cache directory in some environments.

## Next Phase Readiness

`Heatmap`'s `items: HeatmapItem[] | null` prop and `MainChart`'s `{ ticker, points, price, changePercent }` prop contract are stable for Plan 05's final grid layout, which only repositions these panels' mount points into the desktop grid (heatmap alongside the P&L chart in a 2-column sub-grid, main chart above them) — no interface changes expected. Task 1's human-check (browser verification of zero/one/many-position heatmap rendering and colour-independence) and Task 2's human-check (click-to-select main chart behavior, remove-control isolation, long-running line extension) were not run against a live `uvicorn` server serving the static export in this execution — both are automated-verify-clean (tests/lint/build all pass) but are flagged as deferred manual checks for phase-level UAT, matching the precedent set by every prior plan in this phase.

## Known Stubs

None — no hardcoded empty values or placeholder text were introduced. The heatmap renders real `derivePositionRows` output with no minimum-size floor or synthesized data; the main chart renders real accumulated `PricePoint[]` history with no synthesized baseline or interpolation.

## Threat Flags

None — all new surfaces (`HeatmapCell`/`Heatmap`'s rendering of server-supplied position values and ticker text, `MainChart`'s rendering of ticker/price text and accumulated history) were already registered and dispositioned in this plan's own `<threat_model>` (T-03-11 through T-03-14, T-03-SC), with no additional surface introduced beyond what was planned.

## Self-Check: PASSED

All created files verified present on disk; all task commits (`273df69`, `c82be22`) and this summary's commit (`b3f132a`) verified present in `git log`.

---
*Phase: 03-visual-terminal-watchlist-control*
*Completed: 2026-08-17*
