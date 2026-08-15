---
phase: 01-live-streaming-terminal
plan: 04
subsystem: ui
tags: [react, next.js, eventsource, sse, connection-state, accessibility, vitest]

# Dependency graph
requires:
  - phase: 01-live-streaming-terminal (01-02)
    provides: ConnectionStatus union in frontend/lib/types.ts, Header component with a reserved right-hand slot, dark terminal theme with --up/--down/--reconnecting semantic status variables, vitest test harness
provides:
  - Pure, time-injected three-state connection reducer (frontend/lib/connection.ts) with staleness detection
  - ConnectionIndicator component rendering the header dot + fixed-string label, with an accessible description for the disconnected state
  - usePriceStream rewired to feed real EventSource events plus a periodic staleness tick into the reducer
affects: [phase-2-portfolio-trading, phase-3-watchlist-curation]

actuals:
  tokens: 2600
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Pure reducer with injected clock (`now` parameter) for testable time-based state transitions — no fake timers needed"
    - "Fixed-enum visible label + longer accessible description via aria-describedby, avoiding both a truncation-prone free-text label and a separate error banner"

key-files:
  created:
    - frontend/lib/connection.ts
    - frontend/lib/connection.test.ts
    - frontend/components/ConnectionIndicator.tsx
  modified:
    - frontend/lib/usePriceStream.ts
    - frontend/components/Header.tsx
    - frontend/app/page.tsx

key-decisions:
  - "Kept the visible connection label to the three-string enum (Connected/Reconnecting/Disconnected) and carried the longer UI-SPEC error sentence as an aria-describedby accessible description instead of the literal visible label, per the plan's flagged assumption #3."
  - "Dispatched a 2-second interval 'tick' event from usePriceStream so a wedged-but-open EventSource is caught by the STALE_AFTER_MS=10000 rule, rather than trusting readyState alone."

requirements-completed: [MARKET-03]

coverage:
  - id: D1
    description: "Pure three-state connection reducer (connected/reconnecting/disconnected) with automatic recovery and a staleness downgrade, covered by 11 unit tests"
    requirement: "MARKET-03"
    verification:
      - kind: unit
        ref: "frontend/lib/connection.test.ts (11 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Header connection dot renders the correct color/label for each state and recovers to green automatically when the backend returns, without blanking watchlist prices"
    requirement: "MARKET-03"
    verification:
      - kind: unit
        ref: "frontend/lib/format.test.ts + frontend/lib/connection.test.ts (full suite, 20 tests) plus grep-based acceptance criteria in 01-04-PLAN.md"
        status: pass
    human_judgment: true
    rationale: "The plan's <verify> for Task 2 includes a live human-check step (kill/restart the backend against a served build) that cannot be executed by this automated executor — no running backend or browser session is available in this worktree."

duration: 15min
completed: 2026-08-14
status: complete
---

# Phase 1 Plan 4: Connection Status Indicator Summary

**Three-state (green/yellow/red) header connection indicator driven by a pure, time-injected reducer that treats a stream as unhealthy once price events stop arriving, not merely when the EventSource claims to be open.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-14T21:50:00-04:00 (approx.)
- **Completed:** 2026-08-14T22:05:00-04:00 (approx.)
- **Tasks:** 2
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments
- `frontend/lib/connection.ts`: a pure `reduceConnection` reducer over `open`/`message`/`error`/`tick` events, with `DISCONNECTED_AFTER_ERRORS=3` and `STALE_AFTER_MS=10000`, fully time-injected (no `Date.now()`/`performance.now()` inside the module) so retry escalation and staleness are unit-testable without fake timers.
- `frontend/lib/connection.test.ts`: 11 passing assertions covering initial state, open/message/error transitions, three-strikes disconnection, automatic recovery on open or message, in-window vs. stale ticks, and the tick-never-upgrades-reconnecting invariant.
- `frontend/components/ConnectionIndicator.tsx`: renders the dot (`bg-up`/`bg-reconnecting`/`bg-down`) and the fixed `statusLabel` text inside a `role="status"` polite live region; while disconnected, an `aria-describedby`-linked `sr-only` span carries the UI-SPEC's longer error sentence.
- `frontend/lib/usePriceStream.ts` rewired: `open`/`message`/`error` from the real `EventSource` plus a 2-second `tick` interval are fed through `reduceConnection`; the price map is untouched on error (still merges only, never clears), and exactly one `EventSource` is constructed — no hand-rolled retry loop.
- `frontend/components/Header.tsx` and `frontend/app/page.tsx` wire `status` from `usePriceStream` through to `ConnectionIndicator` in the header's reserved right-hand slot.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pure connection state machine** - TDD RED/GREEN:
   - `4a77f74` test(01-04): add failing test for connection state machine
   - `69fb866` feat(01-04): implement pure connection state machine
2. **Task 2: Wire the indicator into the stream hook and the header** - `6ed8201` feat(01-04): wire three-state connection indicator into header

**Plan metadata:** SUMMARY commit (this file) — pending

_Task 1 was TDD (`tdd="true"`): test commit confirmed RED (import failure) before the implementation commit turned it GREEN (11/11 passing)._

## Files Created/Modified
- `frontend/lib/connection.ts` - Pure three-state reducer (`initialConnectionState`, `reduceConnection`, `statusLabel`) plus `DISCONNECTED_AFTER_ERRORS` and `STALE_AFTER_MS` constants
- `frontend/lib/connection.test.ts` - 11 unit tests covering the full behavior contract from the plan
- `frontend/components/ConnectionIndicator.tsx` - Header dot + label component, `role="status"`, accessible description while disconnected
- `frontend/lib/usePriceStream.ts` - Rewired to dispatch real EventSource events plus a periodic tick into the reducer; price map merge behavior on error unchanged
- `frontend/components/Header.tsx` - Renders `ConnectionIndicator` in its right-hand slot, now takes a `status` prop
- `frontend/app/page.tsx` - Passes `status` from `usePriceStream()` through to `Header`

## Decisions Made
- Visible label stays the fixed three-string enum; the UI-SPEC's longer disconnected sentence is exposed only as an accessible description (`aria-describedby` + `sr-only` span), matching the plan's own flagged assumption #3 rather than replacing the visible label.
- `usePriceStream` ticks every 2 seconds (well under `STALE_AFTER_MS`'s 10-second window) so staleness is detected promptly without adding meaningful render overhead.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed frontend dependencies before running tests**
- **Found during:** Task 1 verification
- **Issue:** `frontend/node_modules` did not exist in this fresh worktree checkout, so `npm test` failed with `vitest: command not found`.
- **Fix:** Ran `npm install` in `frontend/` (existing `package.json`/`package-lock.json`, no new packages added).
- **Files modified:** none tracked (lockfile picked up minor peer-dependency metadata normalization from the local npm resolver; left unstaged as out-of-scope noise per the deviation scope boundary).
- **Verification:** `npm test` then ran and reported results correctly.
- **Committed in:** not committed (pre-existing lockfile noise, out of task scope)

**2. [Rule 3 - Blocking] Updated `frontend/app/page.tsx` to pass `status` through**
- **Found during:** Task 2
- **Issue:** The plan's task action explicitly requires "passing the status through from the page," but `page.tsx` was not listed in the plan's `<files>` for either task. Without this change, `Header` would receive no `status` prop and the indicator would show `undefined`.
- **Fix:** Destructured `status` from `usePriceStream()` in `page.tsx` and passed it to `<Header status={status} />`.
- **Files modified:** `frontend/app/page.tsx`
- **Verification:** `npm run build` (webpack) succeeds with no type errors.
- **Committed in:** `6ed8201` (Task 2 commit)

**3. [Rule 3 - Blocking] Used `next build --webpack` instead of default Turbopack**
- **Found during:** Task 2 verification
- **Issue:** `npm run build` (Turbopack, the project default) fails on this machine with `TurbopackInternalError: ... binding to a port ... Operation not permitted` — a pre-existing local OS port-binding sandbox restriction already documented in STATE.md from Plan 01-02's execution, confirmed unrelated to this plan's code.
- **Fix:** Verified the build with `npx next build --webpack`, which compiles and prerenders cleanly.
- **Files modified:** none (verification workaround only, not a code or config change)
- **Verification:** `npx next build --webpack` exits 0, generates static pages for `/` and `/_not-found`.
- **Committed in:** n/a (no code change)

---

**Total deviations:** 3 auto-fixed (all Rule 3 - blocking issues, no scope creep beyond what the plan's own task action required)
**Impact on plan:** All three were necessary to get the environment and verification working; none altered the plan's intended behavior.

## Issues Encountered
- `gsd-tools.cjs query requirements.mark-complete` failed in this worktree (`GSD runtime library is not built ... tsconfig.build.json not found`). Worked around by manually flipping the `MARKET-03` checkbox and traceability row in `.planning/REQUIREMENTS.md` to match what the tool would have produced.
- The plan's Task 2 `<verify>` includes a `<human-check>` step (kill/restart a running backend, observe the dot in a browser) that this automated worktree executor cannot perform — no backend process or browser session exists in this context. Recorded as `human_judgment: true` in the `coverage` block above (D2) so verify-work routes it to a human rather than silently auto-passing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `ConnectionIndicator` and the reducer pattern (`frontend/lib/connection.ts`) are available for reuse if later phases need similar health-signal UI (e.g., chat panel loading/error states).
- Recommended before shipping this phase: a manual live-resilience check per the plan's `<verify>` — serve the export through FastAPI, stop/restart `uvicorn`, and confirm the dot cycles green → yellow → red → green while watchlist rows retain their last prices throughout.
- No blockers for Phase 2 (Portfolio & Trading).

---
*Phase: 01-live-streaming-terminal*
*Completed: 2026-08-14*

## Self-Check: PASSED

All created/modified files found on disk (connection.ts, connection.test.ts, ConnectionIndicator.tsx, usePriceStream.ts, Header.tsx, page.tsx, this SUMMARY). All task commit hashes (4a77f74, 69fb866, 6ed8201) verified present in `git log --oneline --all`.
