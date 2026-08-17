---
phase: 03-visual-terminal-watchlist-control
plan: 05
subsystem: frontend
tags: [nextjs, react, tailwind, layout, grid, responsive]

requires:
  - phase: 03-visual-terminal-watchlist-control
    plan: "02"
    provides: "Watchlist.tsx / WatchlistRow.tsx five-column row grid and history/onAdded/onRemove props this plan repositions unchanged"
  - phase: 03-visual-terminal-watchlist-control
    plan: "03"
    provides: "PnlChart.tsx's h-64 container and portfolioHistory state this plan mounts into the new heatmap/P&L sub-grid"
  - phase: 03-visual-terminal-watchlist-control
    plan: "04"
    provides: "Heatmap.tsx and MainChart.tsx components and their h-64/h-96 container heights this plan repositions unchanged"
provides:
  - "frontend/components/ChatPlaceholder.tsx: reserved, non-interactive AI chat panel slot (D-03), h-64/min-h-64, exact UI-SPEC copy, no Accent Yellow"
  - "frontend/app/page.tsx: the complete eight-panel terminal grid — fixed 420px watchlist column beside a min-w-0 flexible column, column-direction below lg and row-direction at lg and above"
affects: []

actuals:
  tokens: 1582
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "ChatPlaceholder mirrors PositionsTable/Heatmap's centred empty-state layout (flex flex-col items-center justify-center gap-2 text-center) inside an h-64/min-h-64 box, with no separate section-level heading distinct from the empty-state heading itself — a single 'AI Copilot' heading over the body sentence, not a title-plus-empty-state pair"
    - "Two-column desktop region: flex flex-col lg:flex-row gap-8, first child a lg:w-[420px] lg:shrink-0 watchlist wrapper, second child a flex min-w-0 flex-1 flex-col gap-8 column holding MainChart, a heatmap/P&L 2-col sub-grid, PositionsTable, and ChatPlaceholder"
    - "No panel wrapper sets an explicit height — every chart/heatmap/placeholder keeps owning its own container height (h-96/h-64), so the grid cannot collapse or override a chart's box"

key-files:
  created:
    - frontend/components/ChatPlaceholder.tsx
  modified:
    - frontend/app/page.tsx
    - frontend/components/Watchlist.tsx
    - frontend/components/WatchlistRow.tsx

key-decisions:
  - "ChatPlaceholder has one heading ('AI Copilot'), not a section-title-plus-empty-state-heading pair — the plan's own acceptance criterion (grep -c 'AI Copilot' outputs exactly 1) rules out the two-heading pattern PositionsTable/Heatmap use for their empty states, since the chat panel has no populated state this phase to distinguish a title from"
  - "Watchlist panel padding reduced p-6 -> p-4 (24px -> 16px) and every occurrence of the row grid's horizontal padding (header labels, skeleton rows, WatchlistRow itself, and the inline row-error paragraph) reduced px-4 -> px-2 (16px -> 8px) together, so the header labels, skeleton rows, live rows, and error text all stay column-aligned at the new 420px width — the plan named only 'the watchlist row's' padding explicitly, but leaving the header/skeleton/error paragraphs at px-4 would have visibly misaligned them against the row cells"
  - "Two-column region is a sibling of TradeBar inside <main>, not a new outer wrapper replacing <main> — <main>'s own gap raised from gap-4 to gap-8 (UI-SPEC's 32px layout-gap token) governs the vertical gaps between the disclaimer, TradeBar, and the two-column region itself"

patterns-established:
  - "Fixed-left-column-plus-min-w-0-flexible-column is the terminal's final desktop grid shape for this phase; any future left-rail panel should reuse the lg:w-[Npx] lg:shrink-0 pattern rather than a CSS grid template, since flexbox's shrink-0 is what pins the column width without fighting content-based sizing"

requirements-completed: [UI-02, UI-04]

coverage:
  - id: D1
    description: "All eight panels — header, trade bar, watchlist, main chart, heatmap, P&L chart, positions table, AI chat panel — render on a wide desktop screen in the declared order, two-column at lg and above"
    requirement: UI-02
    verification:
      - kind: automated
        ref: "grep checks on frontend/app/page.tsx (lg:flex-row, lg:w-[420px], lg:grid-cols-2, min-w-0, <ChatPlaceholder present; disclaimer line precedes TradeBar line; no h-[ / style height override) — all pass"
        status: pass
      - kind: automated
        ref: "cd frontend && npm test && npm run lint && npx next build --webpack — 95 tests pass, lint clean, build succeeds"
        status: pass
      - kind: manual
        ref: "Task 2 human-check (wide-desktop layout, resize to ~800px, resize back, empty-watchlist stability) — deferred to phase UAT per the auto-mode tracer-gate precedent set in 03-01 through 03-04"
        status: deferred
    human_judgment: true
  - id: D2
    description: "Below lg (1024px) every panel stacks full-width in one vertically scrolling column in the same declared order, nothing hidden or collapsed"
    requirement: UI-04
    verification:
      - kind: automated
        ref: "grep -Ec 'hidden|lg:hidden|max-lg:hidden' frontend/app/page.tsx outputs 0; the two-column region is column-direction by default (flex flex-col, lg:flex-row), so no separate tablet-only branch exists — the stack is a structural consequence, not conditional logic"
        status: pass
      - kind: manual
        ref: "Task 2 human-check (narrow to ~800px, confirm single-column stack with both charts still rendering) — deferred to phase UAT"
        status: deferred
    human_judgment: true
  - id: D3
    description: "The AI chat panel is a reserved, correctly-sized, non-interactive slot matching the heatmap/P&L chart height, carrying the exact UI-SPEC copy and no interactive element or Accent Yellow"
    requirement: UI-02
    verification:
      - kind: automated
        ref: "grep checks on frontend/components/ChatPlaceholder.tsx (AI Copilot count 1, exact body sentence present, zero interactive-element matches, zero ecad0a matches, h-64/min-h-64 present)"
        status: pass
    human_judgment: false

duration: ~6min
completed: 2026-08-17
status: complete
---

# Phase 3 Plan 05: Final Terminal Layout — Eight-Panel Grid + Reserved Chat Slot Summary

**A reserved, non-interactive `ChatPlaceholder` panel sized to match the heatmap and P&L chart, and a final `page.tsx` desktop grid — a fixed 420px watchlist column beside a `min-w-0` flexible column holding the main chart, a heatmap/P&L 2-column sub-grid, the positions table, and the chat placeholder — that collapses to a single stacked column below the 1024px breakpoint with nothing hidden or resized.**

## Performance

- **Duration:** ~6 min (measured from prior wave base `5a10b9b` to final task commit `5f5b0c2`)
- **Tasks:** 2 completed
- **Commits:** 2 (both `feat`)
- **Files touched:** 4 (1 created, 3 modified)

## Accomplishments

- `frontend/components/ChatPlaceholder.tsx` — a plain, prop-less, state-less component: `h-64 min-h-64` box matching the Heatmap/PnlChart containers exactly, centred "AI Copilot" heading over the exact UI-SPEC body sentence (with a real em dash), no input/textarea/button/form/handler, no Accent Yellow
- `frontend/app/page.tsx` — assembled the final eight-panel grid: `<main>`'s gap raised to `gap-8` (32px); the two-column region (`flex flex-col lg:flex-row gap-8`) puts the watchlist in a `lg:w-[420px] lg:shrink-0` wrapper and everything else in a `flex min-w-0 flex-1 flex-col gap-8` column (MainChart → `grid grid-cols-1 lg:grid-cols-2 gap-8` sub-grid holding Heatmap and PnlChart → PositionsTable → ChatPlaceholder); no props, state, memo, or fetch handler changed
- `frontend/components/Watchlist.tsx` — panel padding `p-6` → `p-4`; every `px-4` tied to the row grid (column-header labels, skeleton rows, inline row-error text) reduced to `px-2` to stay aligned with the row template at the new column width
- `frontend/components/WatchlistRow.tsx` — row horizontal padding `px-4` → `px-2`, matching the panel/header changes above
- No panel wrapper sets an explicit height anywhere in `page.tsx` — every chart/heatmap/placeholder still owns its own container height, so nothing can collapse under the new grid
- Full frontend suite: 95 passed (unchanged from 03-04's baseline — no new unit-testable logic, this is pure layout), `npm run lint` clean, `npx next build --webpack` succeeds
- Full backend suite: 172 passed, unchanged (this plan touches no backend file)

## Task Commits

Each task was committed atomically:

1. **Task 1: The reserved AI chat panel slot** — `dc8bc11` (feat)
2. **Task 2: The eight-panel terminal grid, desktop and tablet** — `5f5b0c2` (feat)

**Plan metadata:** this summary commit follows.

## Files Created/Modified

- `frontend/components/ChatPlaceholder.tsx` — new file, the reserved chat panel
- `frontend/app/page.tsx` — `ChatPlaceholder` import, the two-column desktop grid, `gap-8` main gap
- `frontend/components/Watchlist.tsx` — `p-4` panel padding, `px-2` header/skeleton/error-text padding
- `frontend/components/WatchlistRow.tsx` — `px-2` row padding

## Decisions Made

- `ChatPlaceholder` uses a single "AI Copilot" heading, not a section-title-plus-empty-state-heading pair like `PositionsTable`/`Heatmap` — the plan's own acceptance criterion requires `AI Copilot` to appear exactly once, which rules out the two-heading empty-state pattern since this panel has no populated state to distinguish a persistent title from
- Every `px-4` tied to the watchlist row grid template (not just `WatchlistRow` itself) was reduced to `px-2` together — the plan named only "the watchlist row's" padding explicitly, but the column-header labels, skeleton placeholder rows, and inline row-error text all share the same `WATCHLIST_ROW_GRID` template and would have visibly misaligned against the live rows if left at `px-4`
- The two-column region is a sibling of `TradeBar` inside the existing `<main>`, not a new wrapper replacing `<main>` — `<main>`'s own `gap-4` → `gap-8` change is what supplies the 32px layout-gap token between the disclaimer, trade bar, and the two-column region itself, per the UI-SPEC's declared spacing scale

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `frontend/node_modules` did not exist in this fresh worktree**
- **Found during:** before Task 1's first test run
- **Issue:** Same finding as every prior plan in this phase — each git worktree needs its own `npm install` since `node_modules` is gitignored
- **Fix:** Ran `npm install` in `frontend/`; reverted the resulting `package-lock.json` normalization diff (`peer`/`optional` metadata churn, no version changes) since it was incidental to this task
- **Files modified:** none tracked (lockfile diff reverted)
- **Verification:** `npm test`, `npm run lint`, `npx next build` all ran cleanly afterward

**2. [Rule 3 - Blocking issue] `npx next build --webpack` needs network access for the Google font CDN**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** Same root cause documented in every prior plan in this phase — `next/font/google` fetches from Google's CDN at build time, which is outside the sandbox's default network allowlist
- **Fix:** Re-ran both build invocations with the sandbox disabled for that one command; confirmed no code fault
- **Files modified:** none
- **Verification:** both builds completed successfully once network access was available

**3. [Rule 3 - Blocking issue] `uv run --extra dev pytest` failed to initialize its cache under the sandbox**
- **Found during:** Task 2's full-stack verification pass (backend suite, unchanged by this plan)
- **Issue:** Same finding as 03-04 — `uv`'s cache directory access (`~/.cache/uv/.../.git`) was denied under the default sandbox's filesystem restrictions
- **Fix:** Re-ran with the sandbox disabled for that one command; this is a local `uv` cache access need, not a code defect
- **Files modified:** none
- **Verification:** 172 passed, unchanged from the prior plan's baseline

**4. [Acceptance-criteria technicality, documented not auto-fixed] `grep -Ec '<Header|<TradeBar|<Watchlist|<MainChart|<Heatmap|<PnlChart|<PositionsTable|<ChatPlaceholder' frontend/app/page.tsx` outputs 9, not the plan's stated 8**
- **Found during:** Task 2 acceptance-criteria verification
- **Issue:** The pattern's `<Watchlist` alternative also matches the pre-existing, unrelated line `const [watchlist, setWatchlist] = useState<WatchlistEntry[] | null>(null);` (the `<` from the generic plus `WatchlistEntry`'s shared prefix). This line predates this plan — before Task 2's edits the file mounted 7 real panels and the same false-positive line, so the grep already returned 8 for the wrong reason (7 real + 1 false positive). Adding the real 8th panel (`ChatPlaceholder`) makes it 8 real + 1 false positive = 9
- **Resolution:** Not code-fixed — renaming the `useState` generic purely to dodge an acceptance-criteria grep would be scope creep unrelated to the task, and the substantive requirement ("all eight panels mounted") is independently verified true: `grep -n` confirms exactly one mount line each for `Header`, `TradeBar`, `Watchlist`, `MainChart`, `Heatmap`, `PnlChart`, `PositionsTable`, and `ChatPlaceholder` (8 real panels, see command output below)
- **Verification:** `grep -nE '<Header|<TradeBar|<Watchlist|<MainChart|<Heatmap|<PnlChart|<PositionsTable|<ChatPlaceholder' frontend/app/page.tsx` shows the 8 real mount lines plus the one pre-existing `useState<WatchlistEntry...>` line, confirmed by manual inspection

---

**Total deviations:** 3 auto-fixed environment/tooling issues (matching the pattern documented in every prior plan this phase) + 1 documented acceptance-criteria grep technicality (not a code defect)
**Impact on plan:** No scope creep. The three environment fixes have no source-code consequence; the grep technicality is a pre-existing false-positive match unrelated to this plan's changes, with the real 8-panel requirement independently confirmed.

## Issues Encountered

None beyond the four items documented above.

## User Setup Required

None — no external service configuration required. Same environment notes as every prior plan in this phase apply: a fresh worktree needs `npm install` in `frontend/` before tests/lint/build will run, a restricted network egress list needs to allow Google's font CDN for `next/font/google`, and `uv run` may need sandbox filesystem restrictions lifted for its cache directory.

## Next Phase Readiness

This plan closes out Phase 3's UI-02/UI-04 requirements and the phase's final layout artifact. `ChatPlaceholder`'s `h-64 min-h-64` slot is the exact container Phase 4's chat panel content should fill without triggering a reflow — Phase 4 replaces this component's contents, not its container or mount point in `page.tsx`. Task 1's human-check (visual height/chrome parity with Heatmap/PnlChart) and Task 2's human-check (wide-desktop layout, narrow-to-800px stack, resize-back chart redraw, empty-watchlist stability) were not run against a live `uvicorn` server serving the static export in this execution — both are automated-verify-clean (tests/lint/build all pass, and every grep-checkable structural claim in the acceptance criteria is independently confirmed) but are flagged as deferred manual checks for phase-level UAT, matching the precedent set by every prior plan in this phase.

## Known Stubs

None — no hardcoded empty values or placeholder text were introduced beyond the intentional, plan-specified `ChatPlaceholder` empty-state copy, which is explicitly D-03's locked decision (a reserved slot, not a stub to be resolved this phase — Phase 4 fills it).

## Threat Flags

None — both threats this plan's own `<threat_model>` registered (T-03-15 disclaimer-ordering, T-03-16 reserved-chat-slot-as-future-rendering-surface) were mitigated exactly as planned: the disclaimer stays the first element inside `<main>` at both widths (verified by the line-order grep check), and `ChatPlaceholder` ships with zero interactive elements or dynamic content (verified by grep). No additional surface introduced beyond what was planned.

## Self-Check: PASSED

All created/modified files verified present on disk; both task commits (`dc8bc11`, `5f5b0c2`) verified present in `git log`.

---
*Phase: 03-visual-terminal-watchlist-control*
*Completed: 2026-08-17*
