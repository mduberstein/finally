---
phase: quick-260817-lcw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/lib/selection.ts
  - frontend/lib/selection.test.ts
  - frontend/app/page.tsx
autonomous: true
requirements: [WR-03]

estimate:
  tokens: 24000
  raw_tokens: 24000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - Removing the currently-selected ticker from the watchlist clears the selection, so MainChart shows only the "Select a ticker from the watchlist to view its price chart." prompt with no ticker symbol, price, or change-percent header above it.
    - Removing a ticker that is NOT the currently-selected one leaves the selection and the MainChart header untouched.
    - Removing a ticker while nothing is selected is a no-op for selection state.
    - Re-adding a previously-removed ticker requires an explicit click to become selected again (removal does not "remember" the old selection).
  artifacts:
    - frontend/lib/selection.ts
    - frontend/lib/selection.test.ts
  key_links:
    - "handleRemove in frontend/app/page.tsx calls setSelectedTicker with clearSelectionIfRemoved inside the same body.removed success branch that already calls setWatchlist"
    - "selectedTicker={null} flows into MainChart's ticker prop, whose `ticker != null` guard (frontend/components/MainChart.tsx:47) is what hides the stale header block"
---

<objective>
Fix WR-03 from `.planning/phases/03-visual-terminal-watchlist-control/03-REVIEW.md`: `frontend/app/page.tsx`'s `handleRemove` updates `watchlist` state but never touches `selectedTicker`. Removing the currently-selected ticker therefore leaves `MainChart`'s header rendering that ticker's symbol, price, and change percent — frozen forever at the value it held at removal, because `usePriceStream`'s `prices` map is never pruned and the backend `MarketFeed` stops requesting quotes for off-watchlist tickers. The chart body directly beneath simultaneously says "Select a ticker from the watchlist", so the panel contradicts itself.

Purpose: Remove a stale, silently-wrong price from the most prominent chart panel on the page. A frozen price with no staleness indicator is actively misleading in a trading UI.

Output: A pure `clearSelectionIfRemoved` helper in `frontend/lib/selection.ts` with unit tests, wired into `handleRemove` in `frontend/app/page.tsx`.
</objective>

<execution_context>
@/Users/mdub/SOFT-DEV/GitHubRepos/AIProjects/finally/.claude/gsd-core/workflows/execute-plan.md
@/Users/mdub/SOFT-DEV/GitHubRepos/AIProjects/finally/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/03-visual-terminal-watchlist-control/03-REVIEW.md

@frontend/app/page.tsx
@frontend/lib/priceHistory.ts
@frontend/components/MainChart.tsx
</context>

<design_notes>
**Why a `lib/` helper instead of the inline ternary the review suggested.**

`frontend/` has no React Testing Library and no component tests — every one of its 95 tests is a pure-function unit test over a `lib/*.ts` module (`heatmap`, `portfolio`, `priceHistory`, `watchlistForm`, `trade`, `flash`, `format`, `connection`). Putting the invalidation rule inline in `page.tsx` would land it in the one part of the codebase with zero automated coverage. Extracting it follows the established seam: `pruneToWatchlist` (`frontend/lib/priceHistory.ts:53-63`) is an equally small filter that lives in `lib/` with tests precisely so the component stays a thin wiring layer. Do NOT add a testing-library dependency for this — the existing pattern already solves it.

**Scope boundary.** Fix only the manual-remove path in `handleRemove`. Phase 4's LLM-initiated `watchlist_changes` removals will route through their own handler; wiring that path is Phase 4's job, not this fix's. The helper is written so Phase 4 can reuse it directly.
</design_notes>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Clear the selection when the selected ticker is removed</name>
  <files>frontend/lib/selection.ts, frontend/lib/selection.test.ts, frontend/app/page.tsx</files>
  <precondition>`frontend/node_modules` is installed. A fresh git worktree has none (it is gitignored) — run `npm install` in `frontend/` before any test, lint, or build command in this plan. Halt if `npm install` fails.</precondition>
  <behavior>
    `clearSelectionIfRemoved(current: string | null, removed: string): string | null`
    - Test 1: current "AAPL", removed "AAPL" returns null (the WR-03 case)
    - Test 2: current "AAPL", removed "TSLA" returns "AAPL" (unrelated removal preserves selection)
    - Test 3: current null, removed "AAPL" returns null (nothing selected, no-op)
    - Test 4: returns the identical string reference when preserving, so React bails out of a redundant re-render
  </behavior>
  <action>
    Write `frontend/lib/selection.test.ts` FIRST, covering the four cases in `<behavior>`. Run it and confirm it fails (module does not exist yet) before writing any implementation.

    Then create `frontend/lib/selection.ts` exporting a single pure function `clearSelectionIfRemoved(current: string | null, removed: string): string | null` that returns `null` when `current` equals `removed` and returns `current` unchanged otherwise. No normalization, no trimming, no case-folding — the caller passes the same ticker string it already used to build the DELETE URL, and `WatchlistEntry.ticker` values are already backend-normalized uppercase. Give it a docstring naming WR-03 and stating why the stale value is dangerous (the `prices` map from `usePriceStream` is never pruned, so an off-watchlist ticker's entry freezes at its last tick rather than disappearing).

    Then wire it into `handleRemove` in `frontend/app/page.tsx` (lines 108-122): import it from `@/lib/selection`, and inside the existing `if (body.removed)` branch — alongside the `setWatchlist` call that is already there — add `setSelectedTicker((current) => clearSelectionIfRemoved(current, ticker));`. Use the functional updater form, not a bare `selectedTicker === ticker` read, because `handleRemove` closes over a possibly-stale render's `selectedTicker`. Place the new call after `setWatchlist` so the reading order matches the visual order (list first, then the chart that depends on it). Leave the existing comment about the portfolio refetch in place and leave every other line of `handleRemove` — the `!response.ok` early return, the `return true`, the `catch` — exactly as-is.

    Match the surrounding file conventions: named export, explicit return type on the signature, double-quoted imports, and the `@/lib/...` alias.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npx vitest run lib/selection.test.ts</automated>
    <automated>cd frontend &amp;&amp; grep -n 'clearSelectionIfRemoved' app/page.tsx</automated>
  </verify>
  <done>`lib/selection.test.ts` passes all four cases, and `app/page.tsx` calls `clearSelectionIfRemoved` inside `handleRemove`'s `body.removed` branch via `setSelectedTicker`'s functional updater.</done>
</task>

<task type="auto">
  <name>Task 2: Regression gate — full suite, types, lint, production build</name>
  <files>frontend/app/page.tsx, frontend/lib/selection.ts, frontend/lib/selection.test.ts</files>
  <action>
    Run the full frontend gate and fix anything the change broke. Do not modify test expectations to make a failure go away — if an existing test fails, the wiring in Task 1 is wrong; fix the wiring.

    Build with the webpack builder (`npx next build --webpack`), NOT Turbopack — this is the project's established production build invocation and Turbopack has not been validated here.

    No new npm packages are introduced by this plan, so no package-legitimacy audit is required; `npm install` only restores the existing `package-lock.json`.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npx vitest run</automated>
    <automated>cd frontend &amp;&amp; npx tsc --noEmit</automated>
    <automated>cd frontend &amp;&amp; npx eslint</automated>
    <automated>cd frontend &amp;&amp; npx next build --webpack</automated>
    <human-check>Start the app, click a watchlist ticker so its chart loads, then click that row's remove control. The Chart panel should drop the ticker symbol / price / change-percent header entirely and show only the "Select a ticker from the watchlist to view its price chart." prompt. Then select a different ticker and remove a third, unrelated one — the selected chart must keep updating live and keep its header.</human-check>
  </verify>
  <done>All frontend tests pass (95 prior + the 4 new), `tsc --noEmit` is clean, `eslint` is clean, and `next build --webpack` succeeds.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser React state → rendered UI | No new boundary crossed. This change is entirely client-side state invalidation; it sends no new request, accepts no new input, and reads no new data. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-lcw-01 | Tampering | `MainChart` header price display | low | mitigate | This plan IS the mitigation: a frozen, no-longer-tracked price presented with the same visual treatment as a live one misrepresents market state to the user. Clearing `selectedTicker` removes the display entirely rather than showing stale data. |
| T-lcw-02 | Information Disclosure | `clearSelectionIfRemoved` | low | accept | The helper handles only a ticker symbol already visible on screen. No secrets, no PII, no cross-user data — single-user app with hardcoded `user_id="default"`. |
| T-lcw-03 | Denial of Service | `setSelectedTicker` re-render on every removal | low | accept | The helper returns the identical string reference when preserving the selection, so React's state bail-out prevents a re-render on unrelated removals. Worst case is one extra render per removal of the selected ticker. |

No package-manager install tasks are introduced (no new dependencies), so the supply-chain threat class does not apply to this plan.
</threat_model>

<verification>
- `cd frontend && npx vitest run` — full suite green, test count increased by 4
- `cd frontend && npx tsc --noEmit` — no type errors
- `cd frontend && npx eslint` — no lint errors
- `cd frontend && npx next build --webpack` — production static export succeeds
- `grep -n 'clearSelectionIfRemoved' frontend/app/page.tsx frontend/lib/selection.ts frontend/lib/selection.test.ts` — helper defined, tested, and wired
</verification>

<success_criteria>
- Removing the currently-selected ticker leaves `MainChart` showing only its prompt, with no ticker/price/percent header
- Removing any other ticker leaves the current selection and its live-updating header intact
- `frontend/lib/selection.ts` is a pure, dependency-free module reusable by Phase 4's LLM-initiated watchlist removals
- No new npm dependencies added
- WR-03 in `.planning/phases/03-visual-terminal-watchlist-control/03-REVIEW.md` is closed
</success_criteria>

<output>
Create `.planning/quick/260817-lcw-fix-page-tsx-watchlist-remove-handler-to/260817-lcw-SUMMARY.md` when done
</output>
