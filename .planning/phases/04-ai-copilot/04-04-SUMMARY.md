---
phase: 04-ai-copilot
plan: 04
subsystem: frontend
tags: [react, nextjs, chat, typescript, action-cards]

requires:
  - phase: 04-ai-copilot
    provides: "Plan 02's ChatPanel/ChatMessage shell, permissive ChatAction type, and lib/chat.ts transcript helpers"
  - phase: 04-ai-copilot
    provides: "Plan 03's execute_actions()/POST /api/chat action-payload contract (type/status/ticker/side/quantity/price/action/code keys), documented in backend/app/chat/models.py"
provides:
  - "actionCardText(action: unknown) — the sole honesty gate deciding whether an action rendered a card (D-04, T-04-22)"
  - "ChatActionCard — bordered, green-striped confirmation card, no render path other than actionCardText's non-null return"
  - "ChatAction narrowed into a trade/watchlist discriminated union"
  - "clearSelectionIfAbsent(current, tickers) — clears the main-chart selection when a refetched ticker list no longer contains it"
  - "ChatPanel's onActed callback, firing only when a chat turn executed at least one action"
  - "page.tsx's fetchWatchlist callback and handleChatActed, wiring chat-driven changes into the same refresh path as manual trades"
affects: [phase 05 E2E suite (action-card and terminal-refresh scenarios)]

actuals:
  tokens: 9500
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Single honesty-gate function (actionCardText) decides both what card text to show AND whether onActed fires — one function owns 'what counts as something having happened'"
    - "Selection reconciliation helpers (clearSelectionIfRemoved, clearSelectionIfAbsent) return the same reference when unchanged, so React bails out of redundant re-renders"
    - "Hand-built presentation component (ChatActionCard) rather than a new shadcn primitive, per the UI-SPEC's Design System note"

key-files:
  created:
    - frontend/components/ChatActionCard.tsx
  modified:
    - frontend/lib/chat.ts
    - frontend/lib/chat.test.ts
    - frontend/components/ChatPanel.tsx
    - frontend/app/page.tsx
    - frontend/lib/selection.ts
    - frontend/lib/selection.test.ts

key-decisions:
  - "onActed fires only when actionCardText returns non-null for at least one action in the reply — a pure-analysis turn never triggers the four-endpoint refetch"
  - "A message's action cards are computed once as a filtered array (cards.length > 0 ? cards.map(...) : undefined) rather than mapping raw actions through ChatActionCard directly, so an all-failed turn passes no children at all instead of an empty wrapper div"
  - "clearSelectionIfAbsent is a sibling to clearSelectionIfRemoved, not a generalization of it — the click-to-remove path and its existing tests stay untouched"

requirements-completed: [CHAT-03, CHAT-04, CHAT-05]

coverage:
  - id: D1
    description: "An executed trade renders a bordered card with a checkmark, Bought/Sold, quantity, ticker, and exact fill price (CHAT-03, D-04)"
    requirement: "CHAT-03"
    verification:
      - kind: unit
        ref: "frontend/lib/chat.test.ts#actionCardText (executed buy/sell cases)"
        status: pass
      - kind: manual
        ref: "Task 3 Criterion 2 — human browser verification"
        status: pass
    human_judgment: true
  - id: D2
    description: "An executed watchlist change renders a bordered card with a checkmark, Added/Removed, and the ticker (CHAT-04, D-04)"
    requirement: "CHAT-04"
    verification:
      - kind: unit
        ref: "frontend/lib/chat.test.ts#actionCardText (executed watchlist add/remove cases)"
        status: pass
      - kind: manual
        ref: "Task 3 Criterion 3 — human browser verification"
        status: pass
    human_judgment: true
  - id: D3
    description: "A failed trade or watchlist change renders no action card — the explanation lives entirely in prose (CHAT-05)"
    requirement: "CHAT-05"
    verification:
      - kind: unit
        ref: "frontend/lib/chat.test.ts#actionCardText (failed trade/watchlist, unrecognized type, malformed payload cases)"
        status: pass
      - kind: manual
        ref: "Task 3 Criterion 4 — unaffordable-buy check, human browser verification"
        status: pass
    human_judgment: true
  - id: D4
    description: "After a chat turn that executed an action, header cash/total value, positions, heatmap, P&L chart, and watchlist all update without a reload"
    verification:
      - kind: manual
        ref: "Task 3 Criteria 2-3 — human browser verification"
        status: pass
    human_judgment: true
  - id: D5
    description: "A chat-driven removal of the charted ticker clears the main-chart selection instead of freezing on a stale price"
    verification:
      - kind: unit
        ref: "frontend/lib/selection.test.ts#clearSelectionIfAbsent"
        status: pass
      - kind: manual
        ref: "Task 3 removal check — human browser verification"
        status: pass
    human_judgment: true
  - id: D6
    description: "Restored history renders its persisted action cards identically to the live turn"
    verification:
      - kind: manual
        ref: "Task 3 Criterion 5 — reload check, human browser verification"
        status: pass
    human_judgment: true
  - id: D7
    description: "All five ROADMAP Phase 4 success criteria pass end-to-end in a real browser, including the unprompted-suggestion check"
    verification:
      - kind: manual
        ref: "Task 3 — human browser verification, approved"
        status: pass
    human_judgment: true

duration: 12min
completed: 2026-08-18
status: complete
---

# Phase 04 Plan 04: Executed-Action Cards and Terminal Refresh Summary

**Executed trades and watchlist changes now surface as unmistakable bordered green-striped cards beneath the assistant's reply, refusals stay pure prose, and the rest of the terminal (cash, total value, positions, heatmap, P&L chart, watchlist, main chart selection) catches up live with no reload — closing the user-facing loop on CHAT-03, CHAT-04, and CHAT-05.**

## Performance

- **Duration:** ~12 min automated execution + human browser checkpoint
- **Tasks:** 3 (2 automated, 1 checkpoint:human-verify)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- `actionCardText(action: unknown): string | null` — the single honesty gate: returns null unless `status` is exactly `"executed"`, then dispatches on `type` with `typeof`-guarded field checks mirroring `tradeErrorMessage`'s defensive posture, since these payloads originate from a model rather than this codebase
- `ChatActionCard` — a hand-built bordered card (`rounded-md border border-border bg-card px-3 py-2 text-body border-l-2 border-l-up`) with a 14px `CheckCircle2` and `numeric` tabular-figure text; its only render path is `actionCardText`'s non-null return, so a card can never imply something that didn't happen (T-04-22)
- `ChatAction` narrowed from Plan 02's permissive placeholder into a `TradeChatAction | WatchlistChatAction` discriminated union
- `ChatPanel` renders one card per executed action beneath each assistant bubble (stacked `mt-1`), computed as a filtered array so an all-failed turn passes no children — visually identical to a pure-analysis turn
- `ChatPanel`'s new `onActed` prop fires only when the reply contains at least one action `actionCardText` accepts, avoiding wasted refetches on pure-analysis turns (T-04-26)
- `page.tsx` extracts `fetchWatchlist` into a `useCallback`, reconciling the main-chart selection via the new `clearSelectionIfAbsent` after every refetch — so a chat-driven ticker removal clears the header instead of freezing on a stale price (T-04-25)
- `handleChatActed` re-runs `fetchPortfolio`, `fetchPortfolioHistory`, and `fetchWatchlist` — the same refresh the manual trade bar already triggers, plus watchlist since chat can also change it
- `clearSelectionIfAbsent(current, tickers)` added beside the existing `clearSelectionIfRemoved`, with the same reference-stability contract, unit-pinned with 5 new cases

## Task Commits

1. **Task 1: Executed-action copy and the bordered action card** — `e89b080` (feat)
2. **Task 2: Cards in the transcript and a terminal that catches up after a chat-driven change** — `36dc45b` (feat)
3. **Task 3: End-to-end phase verification in a real browser** — checkpoint, no code changes; human-approved (see Verification below)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `frontend/lib/chat.ts` — Narrowed `ChatAction` into `TradeChatAction | WatchlistChatAction`; added `actionCardText()`
- `frontend/lib/chat.test.ts` — Extended with 13 new `actionCardText` cases (executed buy/sell, executed add/remove, failed trade/watchlist, unrecognized type, missing/non-number price, invalid watchlist action, null/undefined/non-object)
- `frontend/components/ChatActionCard.tsx` — New: the bordered action card component
- `frontend/components/ChatPanel.tsx` — Added card rendering per assistant message and the `onActed` prop/callback
- `frontend/app/page.tsx` — Extracted `fetchWatchlist` as a `useCallback` with selection reconciliation; added `handleChatActed`; wired `<ChatPanel onActed={handleChatActed} />`
- `frontend/lib/selection.ts` — Added `clearSelectionIfAbsent()`
- `frontend/lib/selection.test.ts` — Extended with 5 new cases

## Decisions Made

- `onActed` gates on `actionCardText` returning non-null for at least one action, so exactly one function decides "something happened" for both card rendering and the refresh trigger (assumption 1 from PLAN.md, confirmed correct in browser testing)
- Card rendering computes a filtered `cards` array first and passes `undefined` (not an empty array) as `ChatMessage`'s children when there are no executed actions — avoids an empty `mt-2` wrapper div on pure-analysis or all-failed turns, which the plan's action text didn't spell out but is necessary to satisfy "the bubble looks exactly as it does for a pure-analysis turn" (Discretion resolution 4)
- `clearSelectionIfAbsent` is a sibling helper, not a widened `clearSelectionIfRemoved` — keeps the click-to-remove path and its existing tests untouched, per assumption 2

## Deviations from Plan

### Acceptance-criteria grep-count imprecision (non-functional)

**1. `clearSelectionIfAbsent` occurrence count in `page.tsx`**

Task 2's acceptance criteria specified `grep -c 'clearSelectionIfAbsent' frontend/app/page.tsx` should output exactly `1`. The correct, working implementation produces `2` — one line for the `import { clearSelectionIfAbsent, clearSelectionIfRemoved } from "@/lib/selection";` statement and one line for the call site inside `fetchWatchlist`. This is the same import+call pattern the pre-existing `clearSelectionIfRemoved` already follows in this file (also 2 lines, import + `handleRemove`'s call), so the plan's expected count of `1` was not achievable without either omitting the import (impossible in TypeScript) or inlining a fully-qualified module reference (a departure from every other import in the file). No functional impact: `clearSelectionIfAbsent` is correctly imported, called once in `fetchWatchlist`'s success path, unit-tested with 5 cases, and confirmed working end-to-end in Task 3's human browser checkpoint (ticker-removal-clears-chart check passed).

**Impact on plan:** None on functionality. All other acceptance-criteria greps for both tasks passed exactly as specified.

---

**Total deviations:** 1 (acceptance-criteria imprecision only; no code/logic auto-fixes were needed)

## Issues Encountered

None. Both automated tasks implemented directly against the interfaces Plans 02 and 03 already established (`ChatMessage`'s `children` slot, the persisted action-payload contract in `backend/app/chat/models.py`, `fetchPortfolio`/`fetchPortfolioHistory`'s existing `useCallback` pattern) with no blocking issues.

### Process deviation (not functional, consistent with 04-03's precedent)

Both `tdd="true"` (Task 1) and non-TDD (Task 2) tasks combined test/implementation work into a single `feat(...)` commit per task rather than separate `test(...)`/`feat(...)` RED/GREEN commits. Tests were written and passing before each commit (26/26 for Task 1's `chat.test.ts`, 130/130 for Task 2's full suite including 5 new `selection.test.ts` cases), but the two-commit RED/GREEN granularity from `<tdd_execution>` was not followed to the letter. No functional impact — same pattern Plan 03 documented for the same reason (rewriting worktree history to split an already-verified commit is not worth the churn).

## User Setup Required

None for the automated tasks. Task 3's human browser checkpoint required a real `OPENROUTER_API_KEY` in the repo-root `.env` and a locally running server — both already established by Plan 01/03, verified working by the human in this session.

## Next Phase Readiness

- Phase 4 (AI Copilot) is now fully complete: `POST /api/chat`/`GET /api/chat/history` (Plan 01), the chat panel with bubbles/typing dots (Plan 02), live portfolio context and auto-executed actions with exact-numbers refusals (Plan 03), and action cards with terminal-wide refresh (this plan) all verified end-to-end in a real browser against a live OpenRouter/Cerebras key
- All five ROADMAP Phase 4 success criteria passed: portfolio Q&A with real numbers, buy-with-card-and-live-refresh, watchlist add/remove-with-cards-and-streaming, unaffordable-buy refusal with exact figures and zero side effects, and reload persistence + `LLM_MOCK` determinism — plus the unprompted-suggestion check and the chat-driven-removal-clears-chart bonus check
- Backend suite: 227 tests, all green, unchanged by this plan (touches no backend file)
- Frontend suite: 125 → 130 tests, all green
- Phase 5 (final polish / E2E, per ROADMAP) can build `LLM_MOCK`-driven Playwright scenarios directly against the now-complete chat action-card and refresh-on-act contract

## Self-Check: PASSED

All 6 modified files, 1 created file, and this SUMMARY.md verified present on disk; both task commits (`e89b080`, `36dc45b`) verified in `git log`.

---

*Phase: 04-ai-copilot*
*Completed: 2026-08-18*
