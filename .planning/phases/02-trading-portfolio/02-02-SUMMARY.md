---
phase: 02-trading-portfolio
plan: 02
subsystem: trading
tags: [fastapi, sqlite, sqlite3-immediate-transaction, react, vitest, next.js, tailwind]

requires:
  - phase: 02-trading-portfolio
    provides: "Plan 02-01's execute_trade buy branch, TradeRejected exception family, portfolio router, and Buy-only TradeBar"
provides:
  - "Sell branch and InsufficientSharesError oversell guard inside execute_trade, sharing the same BEGIN IMMEDIATE transaction as the buy path"
  - "Full TEST-01 backend suite: sell, oversell, append-only history, total-value math, and a threaded concurrent-trade race test"
  - "frontend/lib/trade.ts — pure validateTradeInput and tradeErrorMessage, the single source of the UI-SPEC error copy"
  - "TradeBar with Sell button, disabled-while-invalid-or-in-flight gating, and inline persistent error text (D-04)"
affects: [03-portfolio-visualization, 04-ai-chat]

actuals:
  tokens: 5874
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Sell mirrors buy inside the same BEGIN IMMEDIATE transaction — position read, oversell guard, cash write, and trade insert all happen before COMMIT so the race the concurrency test proves for buy also holds for sell"
    - "Row removal on zero quantity — the only DELETE anywhere in the portfolio package, scoped to `positions` by id, keeping `trades` append-only (PORT-10) verified by a grep gate"
    - "Backend returns a machine-checkable `code` field; frontend owns 100% of user-facing copy in one pure module (trade.ts), matching the layering RESEARCH.md's Architectural Responsibility Map specifies"

key-files:
  created:
    - backend/tests/portfolio/test_service.py (extended)
    - frontend/lib/trade.ts
    - frontend/lib/trade.test.ts
  modified:
    - backend/app/portfolio/service.py
    - backend/tests/portfolio/test_routes.py
    - frontend/components/TradeBar.tsx

key-decisions:
  - "Test names were adjusted to include the acceptance criteria's -k filter keywords (oversell, trade_history) verbatim so pytest -k selection works as specified"
  - "TradeBar renders the neutral fallback message for any non-400 fetch failure or network error, not just an unrecognised backend code, so the inline-error surface never silently does nothing on an unexpected response"

requirements-completed: [PORT-03, PORT-04, PORT-05, UI-03, TEST-01]

coverage:
  - id: D1
    description: "Selling owned shares fills at the cached price, increases cash by quantity x price, and reduces or removes the position"
    requirement: PORT-03
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py#TestExecuteTradeSell.test_partial_sell_increases_cash_and_reduces_position"
        status: pass
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py#TestExecuteTradeSell.test_selling_all_shares_removes_position_row"
        status: pass
    human_judgment: false
  - id: D2
    description: "Overselling and unaffordable buys are refused, leaving cash/positions/trades unchanged"
    requirement: "PORT-04, PORT-05"
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py#TestExecuteTradeSell.test_oversell_by_one_share_raises_insufficient_shares"
        status: pass
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py#TestExecuteTradeSell.test_rejected_sell_leaves_state_unchanged"
        status: pass
      - kind: integration
        ref: "backend/tests/portfolio/test_routes.py#TestTradeRejectionMapping"
        status: pass
    human_judgment: false
  - id: D3
    description: "Trade bar submits Buy or Sell in one click, disables while invalid or in flight, and renders each refusal as the exact inline UI-SPEC sentence, clearing on the next input change"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "frontend/lib/trade.test.ts (12 assertions covering validateTradeInput and tradeErrorMessage)"
        status: pass
    human_judgment: true
    rationale: "Visual/interaction confirmation (button disabled states, exact on-screen error placement and color, error clearing on input change) requires a human looking at the running app per the plan's <human-check> — deferred to end-of-phase UAT per config.json human_verify_mode: end-of-phase."
  - id: D4
    description: "Backend suite covers trade execution, P&L math, insufficient cash, overselling, append-only history, and the concurrent-trade race"
    requirement: TEST-01
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/ (26 tests, full backend suite 137 tests)"
        status: pass
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py#TestConcurrentTrades.test_only_one_of_two_racing_buys_succeeds_when_only_one_is_affordable"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-16
status: complete
---

# Phase 2 Plan 2: Sell Trade Path and Inline Rejection Copy Summary

**Sell branch and oversell guard added to `execute_trade` inside the existing `BEGIN IMMEDIATE` transaction, plus a `frontend/lib/trade.ts` module and Sell button that render every domain rejection as the exact UI-SPEC sentence inline beneath the trade bar.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-16T00:52:00Z
- **Completed:** 2026-08-16T01:17:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- `execute_trade` now handles both buy and sell inside one `BEGIN IMMEDIATE` transaction; a sell reduces the position and appends a trade row, or removes the `positions` row entirely when quantity reaches zero
- `InsufficientSharesError` is raised (owned=0 for no position, owned=N for a partial oversell) and mapped to HTTP 400 with `code: "insufficient_shares"` via the existing `TradeRejected` catch
- Backend TEST-01 suite extended to 26 portfolio tests: sell, all-shares-sell, oversell (unowned and partial), rejected-sell state invariance, append-only trade-count history, total-value/P&L math, and a threaded concurrent-trade race proving `BEGIN IMMEDIATE` serializes two racing buys
- `frontend/lib/trade.ts` is a pure module owning both client-side input validation (whole shares ≥1, ≤5-char ticker, D-02/D-03) and the exact UI-SPEC error sentences for all three backend rejection codes plus a neutral fallback
- `TradeBar` gained a Sell button (outline, `--down` border/text per UI-SPEC, not the shadcn destructive variant), disables both buttons while invalid or in flight, and renders inline persistent error text that clears the moment ticker or quantity changes

## Task Commits

Each task was committed as a RED/GREEN TDD pair:

1. **Task 1: Sell, the oversell guard, and the full TEST-01 backend suite**
   - `c46b2de` (test) — failing tests for sell, oversell, and TEST-01 coverage
   - `7a104aa` (feat) — sell branch and oversell guard in `execute_trade`
2. **Task 2: Sell button, validation gating, and the inline error surface**
   - `65a8804` (test) — failing tests for trade input validation and error copy
   - `ea58d39` (feat) — Sell button, validation gating, and inline trade errors

## Files Created/Modified
- `backend/app/portfolio/service.py` - added `InsufficientSharesError` import and `_apply_sell`, wired the `elif side == "sell"` branch into `execute_trade`
- `backend/tests/portfolio/test_service.py` - added `TestExecuteTradeSell`, `TestAppendOnlyTradeHistory`, `TestConcurrentTrades`, and a total-value/P&L test on `TestGetPortfolio`
- `backend/tests/portfolio/test_routes.py` - added `TestTradeRejectionMapping` (400 code assertions for all three rejections, 422 for a non-numeric quantity)
- `frontend/lib/trade.ts` - new pure module: `MALFORMED_INPUT_MESSAGE`, `validateTradeInput`, `tradeErrorMessage`
- `frontend/lib/trade.test.ts` - 12 assertions covering every behavior-block case
- `frontend/components/TradeBar.tsx` - Sell button, in-flight/invalid disabled gating, inline error region, `maxLength` on the ticker input

## Decisions Made
- Renamed two test methods (`test_oversell_by_one_share_raises_insufficient_shares`, `test_trade_history_count_only_increases_and_rejected_trade_adds_no_row`) so the plan's `pytest -k oversell` / `-k trade_history` acceptance-criteria filters actually select them — the plan's behavior description didn't dictate exact test names, only that the case exists.
- `tradeErrorMessage`'s fallback also covers non-`400`/non-`200` HTTP failures and thrown fetch errors in `TradeBar`, not only an unrecognised `code` string, so the inline-error surface has no silent-failure path.

## Deviations from Plan

None - plan executed exactly as written. Test-name adjustments above are TDD authoring detail, not scope changes.

## Issues Encountered
- `uv`'s global cache directory was unwritable under the default sandbox (pre-existing `.git`-backed cache lookup failing with `Operation not permitted`); backend commands were run with the sandbox override for this reason only — no code or dependency changes resulted.
- The frontend worktree had no `node_modules` (each git worktree needs its own `npm ci`); ran `npm ci` once at the start of Task 2 before any test/lint/build command — clean install from the existing `package-lock.json`, no dependency changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both buy and sell are now fully implemented, tested, and inline-error-complete; Phase 3 (portfolio visualization) can build the heatmap/P&L chart/positions table against a stable `GET /api/portfolio` and `POST /api/portfolio/trade` contract.
- Plan 02-02's `<verify>` block's manual `<human-check>` (visually confirming button disabled states and the four error strings in a running browser) is deferred to end-of-phase UAT per `config.json`'s `human_verify_mode: "end-of-phase"` — not run inside this worktree-isolated agent.

---
*Phase: 02-trading-portfolio*
*Completed: 2026-08-16*
