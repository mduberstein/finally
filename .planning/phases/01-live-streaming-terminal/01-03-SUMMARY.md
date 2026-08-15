---
phase: 01-live-streaming-terminal
plan: 03
subsystem: ui
tags: [react, css-animation, accessibility, vitest, watchlist]

# Dependency graph
requires:
  - phase: 01-live-streaming-terminal (plan 02)
    provides: Dark terminal theme, Header/Watchlist/WatchlistRow decomposition, formatPrice/formatPercent, vitest+jsdom harness
provides:
  - Pure, time-injected flash state machine (frontend/lib/flash.ts)
  - PriceCell component rendering the flashing price cell and the glyph+percent non-color cell
  - flash-up/flash-down CSS keyframes with prefers-reduced-motion suppression
affects: [01-04, phase-3-frontend]

# Actuals (#2632)
actuals:
  tokens: 2762
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure, time-injected state machines (now as a parameter, never read internally) for anything that must be unit-testable without fake timers"
    - "Keying an animated DOM node on a state's startedAt timestamp to force a remount, which restarts a CSS animation from full intensity on a rapid re-trigger"
    - "Direction/status conveyed by both color (flash tint) and a non-color glyph + signed value, satisfying the color-alone accessibility prohibition"

key-files:
  created:
    - frontend/lib/flash.ts
    - frontend/lib/flash.test.ts
    - frontend/components/PriceCell.tsx
  modified:
    - frontend/app/globals.css
    - frontend/components/WatchlistRow.tsx
    - frontend/components/Watchlist.tsx

key-decisions:
  - "Effect that stamps a new FlashState calls setState synchronously from an effect reacting to a prop change (direction/price) — the eslint react-hooks/set-state-in-effect rule flags this, but it's suppressed with a targeted disable comment because the state is synchronized from an external source (wall-clock time via Date.now()), not derived purely from props, which is the anti-pattern the rule targets"
  - "Render-time active/inactive gating uses `flash == null` rather than a live isFlashActive(flash, Date.now()) call, because calling Date.now() during render is flagged by the react-hooks/purity rule; isFlashActive is still exercised inside the clearing effect's setTimeout callback, a legitimate non-render side-effect location"
  - "Direction glyph placed in the percent cell (before the signed percent) rather than the price cell, since the percent cell already carries a sign and the two together read as one non-color signal; the flash tint stays exclusively on the price cell per the UI-SPEC's color table"

patterns-established:
  - "PriceCell is the single place a watchlist row's numeric cells are rendered — both price and percent cells come from one component so the flash/glyph/percent trio can never drift out of sync"

requirements-completed: [MARKET-02]

coverage:
  - id: D1
    description: "Pure flash state machine: nextFlashState, isFlashActive, directionGlyph, FLASH_DURATION_MS — all time-injected, fully unit tested"
    requirement: "MARKET-02"
    verification:
      - kind: unit
        ref: "frontend/lib/flash.test.ts (13 tests: nextFlashState x6, isFlashActive x3, directionGlyph x3, FLASH_DURATION_MS x1)"
        status: pass
      - kind: automated_ui
        ref: "cd frontend && npm run lint"
        status: pass
    human_judgment: false
  - id: D2
    description: "PriceCell flashes green on an uptick, red on a downtick, fades over ~500ms, restarts on a rapid re-tick, and always renders a direction glyph + signed percent regardless of flash state; reduced-motion suppresses the animation only"
    requirement: "MARKET-02"
    verification:
      - kind: automated_ui
        ref: "cd frontend && npm test && npm run lint && npm run build"
        status: pass
      - kind: other
        ref: "grep checks for @keyframes x2, prefers-reduced-motion, 500ms x2, absence of #209dd7 in PriceCell.tsx — all pass"
        status: pass
    human_judgment: true
    rationale: "The plan's own verify block for this task specifies a human-check (sustained observation of the live grid: green/red tints, ~500ms fade, no tint on flat ticks, glyph+percent always present, reduced-motion suppression) that automated build/lint/test cannot confirm visually. Not run this session — flagged as a follow-up manual check before Phase 1 sign-off."

duration: 45min
completed: 2026-08-15
status: complete
---

# Phase 01 Plan 03: Price Flash Animation Summary

**Pure, time-injected flash state machine driving a `PriceCell` component that tints green/red on price ticks and fades over ~500ms, with a triangle glyph + signed percent as the non-color accessibility channel**

## Performance

- **Duration:** 45 min
- **Tasks:** 2 (both complete)
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- `frontend/lib/flash.ts` — pure, time-injected `nextFlashState`, `isFlashActive`, and `directionGlyph` functions plus the `FLASH_DURATION_MS` constant, built via TDD (RED test suite, then GREEN implementation)
- `frontend/components/PriceCell.tsx` — renders the price cell (with the fading flash tint) and the percent cell (with the direction glyph and signed percent) for one watchlist row
- Two CSS keyframes (`flash-up`, `flash-down`) animating `background-color` from a 32%-alpha semantic status color to transparent over 500ms ease-out, added to `frontend/app/globals.css`, suppressed under `prefers-reduced-motion: reduce`
- `WatchlistRow` now renders its numeric cells through `PriceCell`; `Watchlist` threads the live tick's `direction` down to it

## Task Commits

Each task was committed atomically:

1. **Task 1: Pure flash state machine (TDD):**
   - RED: `c5d4b68` (test) — failing `flash.test.ts` covering all 10+ behavior cases from the plan
   - GREEN: `56dd39b` (feat) — `frontend/lib/flash.ts` implemented, all 22 tests (13 flash + 9 formatter) pass
2. **Task 2: PriceCell with the fading tint and direction glyph** — `617bf1d` (feat) — CSS keyframes, `PriceCell` component, `WatchlistRow`/`Watchlist` wiring

_Note: Task 1 is TDD — two commits (test → feat); no refactor commit was needed since the GREEN implementation was already minimal and clean._

## Files Created/Modified

- `frontend/lib/flash.ts` - `FLASH_DURATION_MS`, `FlashState`, `nextFlashState`, `isFlashActive`, `directionGlyph` (Task 1)
- `frontend/lib/flash.test.ts` - 13 tests covering every behavior case from the plan (Task 1)
- `frontend/components/PriceCell.tsx` - price cell (flash tint) + percent cell (glyph + signed percent) (Task 2)
- `frontend/app/globals.css` - `flash-up`/`flash-down` keyframes, `.animate-flash-up`/`.animate-flash-down` utilities, `prefers-reduced-motion` override (Task 2)
- `frontend/components/WatchlistRow.tsx` - renders numeric cells through `PriceCell`, accepts a `direction` prop (Task 2)
- `frontend/components/Watchlist.tsx` - passes the live tick's `direction` (or the entry's null placeholder) down to `WatchlistRow` (Task 2, deviation — see below)

## Decisions Made

- Suppressed a `react-hooks/set-state-in-effect` lint finding with a targeted disable comment: the flagged effect synchronizes flash state with wall-clock time (`Date.now()`), an external source, which is different from the anti-pattern the rule exists to catch (deriving state purely from props, for which React's "adjust state during render" pattern is the fix — not applicable here since render must stay pure and cannot read the clock)
- Kept render-time flash-active gating to `flash == null` rather than a live `isFlashActive(flash, Date.now())` check, since calling `Date.now()` during render is flagged by `react-hooks/purity`; `isFlashActive` is still exercised inside the clearing effect's `setTimeout` callback
- Placed the direction glyph in the percent cell rather than the price cell — the flash tint (color signal) stays exclusively on the price cell per the UI-SPEC color table, while the glyph and signed percent (non-color signal) live together in the adjacent cell

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wired `direction` through `Watchlist.tsx` (file not listed in plan frontmatter)**
- **Found during:** Task 2
- **Issue:** The plan's `files_modified` list covers `WatchlistRow.tsx` but not `Watchlist.tsx`. Without threading the live tick's `direction` field through `Watchlist.tsx` down to `WatchlistRow`/`PriceCell`, the flash feature would receive `direction: undefined` on every render and never fire — the whole feature would be dead code in the running app despite passing all file-local acceptance criteria.
- **Fix:** Added a `direction` line mirroring the existing `price`/`changePercent` derivation (`live?.direction ?? entry.direction`) and passed it to `WatchlistRow`.
- **Files modified:** `frontend/components/Watchlist.tsx`
- **Verification:** `npm test && npm run lint` pass; manual trace of the prop chain confirms `direction` now reaches `PriceCell`
- **Committed in:** `617bf1d` (Task 2 commit)

**2. [Rule 3 - Blocking] Reverted an incidental `package-lock.json` regression from `npm install`**
- **Found during:** Task 1 setup
- **Issue:** This worktree had no `node_modules`, requiring `npm install`. That install re-resolved and re-introduced the exact corrupted `@emnapi/runtime` lockfile entry (missing `version` field) that Plan 01-02 explicitly fixed as a blocking issue, plus two unrelated `peer` flag flips on jsdom/tailwindcss transitive deps.
- **Fix:** `git checkout -- frontend/package-lock.json` before staging any Task 1 files, discarding the regression. `node_modules` on disk remained installed and functional; only the lockfile diff was reverted.
- **Files modified:** none committed (reverted before staging)
- **Verification:** `npm test`, `npm run lint`, `npm run build` all still pass after the revert

**3. [Rule 3 - Blocking] Used `--webpack` to verify the production build**
- **Found during:** Task 2 verification
- **Issue:** The default Turbopack build fails in this environment with `TurbopackInternalError: ... binding to a port ... Operation not permitted` — the same pre-documented local OS port-binding sandbox quirk noted in Plan 01-02's SUMMARY, unrelated to this plan's code.
- **Fix:** Verified with `npx next build --webpack`, which compiles and generates static pages successfully.
- **Files modified:** none
- **Verification:** `npx next build --webpack` exits 0, generates `/` and `/_not-found` as static content

---

**Total deviations:** 3 auto-fixed (all blocking, Rule 3)
**Impact on plan:** No scope creep — one fix makes the feature actually reachable at runtime, one reverts an accidental regression, one substitutes an equivalent verification path for a known environment limitation.

## Issues Encountered

- `npm run build` (Turbopack, default) cannot be used to verify in this sandbox — see deviation 3 above. Any future plan running `npm run build` in this environment should expect the same failure and fall back to `npx next build --webpack`.
- The plan's Task 2 `<verify>` includes a `human-check` (sustained visual observation of the live grid, including a reduced-motion check) that was not run this session — this plan executed autonomously in a parallel worktree with no interactive browser session available. Flagged in the `coverage` frontmatter (D2) as a pending manual check before Phase 1 sign-off.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `PriceCell` and the flash state machine are ready for Plan 04 (connection status indicator) to build alongside, and for Phase 3's sparkline work to read ticks from the same `PriceTick` shape
- The human-check for the live visual flash (green/red tint, ~500ms fade, glyph/percent always present, reduced-motion suppression) should be run once Plan 01-04 lands and the full watchlist grid is exercised end-to-end
- No blockers identified for the remainder of Wave 3 (01-04) or Phase 1 verification

---
*Phase: 01-live-streaming-terminal*
*Completed: 2026-08-15*

## Self-Check: PASSED

All claimed files verified present: `frontend/lib/flash.ts`, `frontend/lib/flash.test.ts`, `frontend/components/PriceCell.tsx`, `frontend/app/globals.css`, `frontend/components/WatchlistRow.tsx`, `frontend/components/Watchlist.tsx`, `.planning/phases/01-live-streaming-terminal/01-03-SUMMARY.md`. All claimed commit hashes verified present in `git log`: `c5d4b68`, `56dd39b`, `617bf1d`.
