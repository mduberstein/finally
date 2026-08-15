---
phase: 01-live-streaming-terminal
plan: 02
subsystem: ui
tags: [nextjs, tailwind, shadcn, vitest, jsdom, dark-theme]

# Dependency graph
requires:
  - phase: 01-live-streaming-terminal (plan 01)
    provides: Next.js static-export scaffold, usePriceStream hook, PriceTick/WatchlistEntry/ConnectionStatus types
provides:
  - Dark terminal CSS theme layered on shadcn neutral tokens (#0d1117/#161b22/#30363d/#209dd7)
  - Header/Watchlist/WatchlistRow component decomposition with loading, empty, and populated states
  - Shared formatPrice/formatPercent formatters with an em-dash null convention
  - Frontend vitest + jsdom test harness (npm test) that every later Phase 1 plan verifies against
affects: [01-03, 01-04, phase-3-frontend]

# Actuals (#2632)
actuals:
  tokens: 4139
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: [vitest@4.1.10, jsdom (~29.1.1, resolved via peer constraints)]
  patterns:
    - "Shared numeric formatters (frontend/lib/format.ts) are the single source of truth for null-safe price/percent rendering — never inline toFixed() at a call site"
    - "vitest.config.ts mirrors the Next.js @/* path alias so test imports resolve identically to app code"

key-files:
  created:
    - frontend/components/Header.tsx
    - frontend/components/Watchlist.tsx
    - frontend/components/ui/skeleton.tsx
    - frontend/lib/format.ts
    - frontend/lib/format.test.ts
    - frontend/vitest.config.ts
  modified:
    - frontend/app/globals.css
    - frontend/app/layout.tsx
    - frontend/app/page.tsx
    - frontend/components/WatchlistRow.tsx
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Named the semantic status CSS variables for role (up/down/reconnecting) rather than color, per the plan's flagged assumption"
  - "formatPrice uses toLocaleString for thousands-separator formatting rather than a manual regex"
  - "Fixed a pre-existing corrupted package-lock.json entry (missing version on a nested @emnapi/runtime optional dependency of sharp-wasm32) that blocked all npm install commands — unrelated to vitest/jsdom but a hard blocker for Task 3 (Rule 3)"

patterns-established:
  - "TDD RED/GREEN commits split test scaffolding (test script, config, failing test) from implementation (formatters, call-site wiring)"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "Dark terminal theme (backgrounds, borders, accent, typography roles, tabular-nums) layered on shadcn tokens; Inter loaded via next/font"
    requirement: "UI-01"
    verification:
      - kind: automated_ui
        ref: "cd frontend && npm run lint && npm run build"
        status: pass
      - kind: other
        ref: "grep checks for #0d1117, #161b22, #30363d, #209dd7, tabular-nums, and absence of #000/font-weight 500|700 in frontend/app/globals.css"
        status: pass
    human_judgment: false
  - id: D2
    description: "Header/Watchlist/WatchlistRow decomposition: 10 skeleton rows while loading, empty-state copy on zero entries, 10 live rows when populated, accent hover/focus stripe on rows"
    requirement: "UI-01"
    verification:
      - kind: automated_ui
        ref: "cd frontend && npm run lint && npm run build"
        status: pass
    human_judgment: true
    rationale: "The plan's own verify block for this task specifies a human-check (skeleton timing, non-jittering price column, hover/focus stripe) that automated build/lint cannot confirm visually."
  - id: D3
    description: "Shared formatPrice/formatPercent formatters (em-dash on null/undefined, thousands separator, signed percent) plus the vitest+jsdom harness wired into npm test"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/lib/format.test.ts (9 tests: formatPrice x4, formatPercent x5)"
        status: pass
    human_judgment: false

duration: 20min (Task 3 only, this session — Tasks 1-2 were completed and committed in a prior session per the resume handoff)
completed: 2026-08-15
status: complete
---

# Phase 01 Plan 02: Dark Terminal Theme, Component Decomposition & Test Harness Summary

**Dark terminal CSS theme with Header/Watchlist/WatchlistRow decomposition and a vitest+jsdom harness backing shared formatPrice/formatPercent formatters**

## Performance

- **Duration:** 20 min (Task 3 completion this session; Tasks 1-2 completed in a prior, paused session)
- **Started:** 2026-08-14T21:40:00-04:00 (approx, this session)
- **Completed:** 2026-08-15T01:49:00Z
- **Tasks:** 3 (all complete)
- **Files modified:** 12 across the plan (6 created, 6 modified)

## Accomplishments
- Dark terminal palette (#0d1117 page, #161b22 panels, #30363d borders, #209dd7 accent) layered onto the shadcn-generated neutral CSS variables, with Inter loaded via `next/font` and a `tabular-nums` utility for every numeric cell
- Tracer page decomposed into `Header`, `Watchlist`, and `WatchlistRow` components with real loading (10 skeleton rows), empty (`No tickers being tracked`), and populated states
- Frontend test runner (vitest + jsdom) stood up from scratch, with `npm test` running once (not watch mode) so the executor's verify command terminates
- `frontend/lib/format.ts` created via TDD (RED then GREEN) exporting `formatPrice`/`formatPercent`, both em-dash-safe on null/undefined; `WatchlistRow` now renders through these shared functions instead of local inline copies

## Task Commits

Each task was committed atomically:

1. **Task 1: Layer the dark terminal theme onto shadcn neutral tokens** - `a206605` (feat) — completed in a prior session
2. **Task 2: Decompose the page into Header, Watchlist, WatchlistRow** - `ba26257` (feat) — completed in a prior session
3. **Task 3: Frontend test runner plus shared numeric formatters (TDD):**
   - RED: `0bcd0ae` (test) — failing `format.test.ts`, vitest+jsdom installed, `npm test` script added
   - GREEN: `dfb16cb` (feat) — `frontend/lib/format.ts` implemented, `WatchlistRow` wired to it, all 9 tests pass

**Plan metadata:** (this commit, docs: complete plan)

_Note: Task 3 is TDD — two commits (test → feat); no refactor commit was needed since the GREEN implementation was already minimal and clean._

## Files Created/Modified
- `frontend/app/globals.css` - Dark terminal CSS variables, typography roles, tabular-nums utility (Task 1)
- `frontend/app/layout.tsx` - Inter font via next/font, dark class on html, page background (Task 1)
- `frontend/app/page.tsx` - Reduced to composition of Header + Watchlist (Task 2)
- `frontend/components/Header.tsx` - Header bar with FinAlly wordmark, slot for connection status (Task 2)
- `frontend/components/Watchlist.tsx` - Loading/empty/populated states for the watchlist panel (Task 2)
- `frontend/components/WatchlistRow.tsx` - One ticker row; now renders through shared formatters (Task 2, updated Task 3)
- `frontend/components/ui/skeleton.tsx` - shadcn-generated skeleton primitive (Task 2)
- `frontend/lib/format.ts` - `formatPrice`/`formatPercent`, em-dash-safe (Task 3)
- `frontend/lib/format.test.ts` - 9 tests covering all behavior cases from the plan (Task 3)
- `frontend/vitest.config.ts` - jsdom environment, `@/*` alias matching the Next.js scaffold (Task 3)
- `frontend/package.json` - `test` script added, vitest+jsdom devDependencies (Task 3)
- `frontend/package-lock.json` - vitest+jsdom resolved; pre-existing corrupted `@emnapi/runtime` entry fixed (Task 3)

## Decisions Made
- Named the semantic status CSS variables for role (up/down/reconnecting) rather than color, per the plan's flagged assumption, so Plans 03/04 read clearly at the call site
- `formatPrice` uses `toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })` for the thousands-separator + fixed-decimal requirement, rather than a manual string-splitting regex
- Tracked row selection in page state per the plan's flagged assumption (no Phase 3 chart destination yet, but the interaction is real)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed corrupted package-lock.json entry blocking all npm install**
- **Found during:** Task 3 (installing vitest + jsdom)
- **Issue:** `node_modules/@img/sharp-wasm32/node_modules/@emnapi/runtime` in `frontend/package-lock.json` was missing its `version` field (only `{"optional": true}`), a pre-existing corruption from an earlier scaffold commit. npm's arborist crashed with `TypeError: Invalid Version` while deduping this entry against the version range `^1.11.1`, blocking every `npm install` in the project — not just the new packages.
- **Fix:** Added the correct `version` (`1.11.3`, the highest version satisfying `^1.11.1`, confirmed via `npm view @emnapi/runtime versions`), plus matching `resolved`, `integrity`, `license`, and `dependencies` fields mirroring the structure of the sibling `@unrs/resolver-binding-wasm32-wasi/node_modules/@emnapi/runtime` entry in the same lockfile.
- **Files modified:** `frontend/package-lock.json`
- **Verification:** `npm install --save-dev vitest jsdom` completed cleanly (669 packages added, 0 vulnerabilities) after the fix
- **Committed in:** `0bcd0ae` (Task 3 RED commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to unblock package installation; no scope creep — the fix touches only the one malformed lockfile entry, not any dependency version this plan actually needed.

## Issues Encountered
- The user's global CLAUDE.md package-legitimacy checkpoint for `vitest` and `jsdom` was resolved before this session started (per the resume handoff) — both packages verified as standard, correctly-named, widely-used npm packages before install.
- vitest's native config loader warns that `vitest.config.ts` uses ESM syntax loaded as CommonJS (`frontend/package.json` has no `"type": "module"`). This is a non-fatal warning only — `npm test` and `npm run build` both exit 0 — and was left as-is since fixing it is out of scope for this task and doesn't affect correctness.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The dark terminal theme, component structure, and vitest harness are in place for Plan 03 (price flash animations, sparklines) and Plan 04 (connection status indicator) to build on
- `npm test` is now the standing frontend test command every later Phase 1 (and Phase 3) plan can add cases to
- No blockers identified for Wave 3 (01-03, 01-04)

---
*Phase: 01-live-streaming-terminal*
*Completed: 2026-08-15*

## Self-Check: PASSED

All claimed files verified present: `frontend/lib/format.ts`, `frontend/lib/format.test.ts`, `frontend/vitest.config.ts`, `.planning/phases/01-live-streaming-terminal/01-02-SUMMARY.md`. All claimed commit hashes verified present in `git log`: `a206605`, `ba26257`, `0bcd0ae`, `dfb16cb`, `2e7df21`.
