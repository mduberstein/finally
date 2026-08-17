---
phase: 02-trading-portfolio
verified: 2026-08-16T06:15:33Z
status: passed
score: 41/41 must-haves verified (5 roadmap success criteria + 36 plan-level truths)
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Stop the backend while the app is running, confirm the header keeps showing its last cash and total value (not zero/blank) and the connection dot goes red; restart the backend and confirm figures resume updating."
    expected: "Header never flashes to $0.00 or blank on a dropped connection; last-good figures persist; dot goes red then back to green."
    why_human: "Visual/real-time behavior across a live disconnect — not observable from a static build or unit test. Deferred from Plan 02-01 Task 2's <human-check> per config.json human_verify_mode: end-of-phase."

  - test: "Click Buy with both fields empty (confirm disabled). Type AAPL and 99999, click Buy (confirm the insufficient-cash sentence appears directly under the inputs naming your actual cash, and clears when quantity changes). Buy 5 AAPL, try to sell 6 (confirm overselling sentence names 5). Sell all 5. Type ZZZZ and 1 (confirm untradable-ticker sentence). Confirm none of these render as a toast or modal."
    expected: "All four error sentences appear inline beneath the trade bar in the exact UI-SPEC copy, clear on next input change, and buttons are visually disabled when appropriate."
    why_human: "Exact on-screen placement, disabled-state styling, and toast/modal absence require visual confirmation in a running browser. Deferred from Plan 02-02 Task 2's <human-check>."

  - test: "With a fresh database, confirm the Positions panel shows the empty-state heading/body. Buy 5 AAPL and 3 NVDA — confirm two rows appear, price/P&L/percent keep changing on their own as prices tick, P&L is green when positive and red when negative. Sell all 5 AAPL — confirm that row disappears immediately (no zero-quantity row). Reload the page — confirm skeleton rows appear briefly instead of an empty-state flash."
    expected: "Empty state, live-moving populated rows with correct coloring, immediate row removal on full sell, and skeleton-before-load ordering all hold visually."
    why_human: "Live color transitions, per-tick movement, and loading-sequence ordering require visual observation in a running browser. Deferred from Plan 02-03 Task 2's <human-check>."

  - test: "Review the 5 judgment-tier prohibitions recorded across the three plans (no shaming/blaming rejection copy, no urgency/dark-pattern trade-bar framing, no simulated money presented as real, no stale price shown as live) against the running app."
    expected: "Each prohibition holds in practice, not just in the reviewed source text."
    why_human: "Prohibition status is `verification: judgment` in all 5 cases — this agent's code-level read (copy text, initial-state code, disclaimer text) is a non-authoritative LLM-judge pass, not a substitute for human sign-off. Flagged per verification-overrides/prohibition routing rules — unverified-prohibition, human review recommended."
---

# Phase 2: Trading & Portfolio Verification Report

**Phase Goal:** A user can buy and sell shares at live market prices and see the portfolio respond immediately
**Verified:** 2026-08-16T06:15:33Z
**Status:** human_needed
**Re-verification:** No — initial verification

**MVP mode note:** ROADMAP.md's `**Goal**:` line for this phase ("A user can buy and sell shares at live market prices and see the portfolio respond immediately") is not itself in `As a ... I want to ... so that ...` format (`user-story.validate` returns `valid: false` against it). All three PLAN.md files for this phase carry an identical, well-formed User Story ("As a trader with $10,000 of simulated cash, I want to buy and sell shares at the live market price and watch my cash, positions, and total value respond immediately, so that the terminal becomes a place I can actually trade rather than only watch.") and `user-story.validate` accepts it. This is a documentation-format gap in ROADMAP.md, not a code gap — the User Flow Coverage below uses the plan-consistent story text. Recommend running `/gsd mvp-phase 2` to backfill the ROADMAP goal line for future automated tooling, but this did not block verification here.

## User Flow Coverage

User story: «As a trader with $10,000 of simulated cash, I want to buy and sell shares at the live market price and watch my cash, positions, and total value respond immediately, so that the terminal becomes a place I can actually trade rather than only watch.»

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Open the app, fresh database | Header shows Cash $10,000.00 and Total Value $10,000.00 | Live `GET /api/portfolio` on a fresh DB returned `{"cash_balance":10000.0,...,"total_value":10000.0,"positions":[]}` (curl, this session); `Header.tsx` renders both via `formatPrice` with a `Skeleton` fallback pre-fetch | ✓ |
| Type ticker + quantity, click Buy | Trade fills instantly at current price, no confirmation dialog, cash drops, position appears in Positions table | Live `POST /api/portfolio/trade {AAPL, buy, 5}` returned a filled `TradeResult` at price 189.98, cash dropped to 9050.10, and a `GET /api/portfolio` immediately after showed the AAPL position (curl, this session); `TradeBar.tsx`/`components/ui/button.tsx` show no modal/dialog component (`grep -Eic 'toast|sonner'` → 0) | ✓ |
| Click Sell on an owned position | Cash increases at the live price; position reduces or disappears if fully sold | Live sell-all-5-AAPL returned cash back to 10000.0 and `GET /api/portfolio` showed `positions: []` (curl, this session); `backend/tests/portfolio/test_service.py::TestExecuteTradeSell` covers the partial-sell case | ✓ |
| Attempt to overbuy or oversell | Refused with a clear on-screen error; cash/positions unchanged | Live oversell of AAPL returned `400 {"code":"insufficient_shares","owned":5.0}`; live untradable-ticker buy returned `400 {"code":"untradable_ticker"}`; `tradeErrorMessage()` maps both (plus `insufficient_cash`) to the exact UI-SPEC sentences, rendered inline (`role="alert"`, `text-down`) in `TradeBar.tsx` | ✓ (mechanism); on-screen placement/styling — see human verification |
| Watch header total value and positions table move with price ticks | Total value and per-position P&L update live, with no page reload and no new network request | `derivePortfolioValue`/`derivePositionRows` are pure functions with 23 unit assertions across changing price maps (`frontend/lib/portfolio.test.ts`, 15 assertions cover this exact contract); `grep -Ec 'setInterval|setTimeout|fetch\(' frontend/lib/portfolio.ts` → 0; `page.tsx` recomputes both via `useMemo` off the single `usePriceStream()` prices object | ✓ (mechanism); live visual "it moves" — see human verification |

All user-flow steps mechanically pass. Two steps have a visual-confirmation component deferred to human verification below (per `config.json`'s `human_verify_mode: end-of-phase`, harvested from the plans' `<human-check>` blocks on `auto` tasks).

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A fresh user starts with $10,000 cash shown in the header | ✓ VERIFIED | Live `GET /api/portfolio` → `cash_balance: 10000.0`; `Header.tsx` renders it via `formatPrice`, skeleton before load |
| 2 | Trade bar buy fills instantly at current price — cash drops, position appears, no confirmation dialog | ✓ VERIFIED | Live buy via curl confirmed fill + cash change + position row; `TradeBar.tsx` has no dialog/confirm step; `grep -Eic 'toast\|sonner'` → 0 |
| 3 | Selling returns cash at the live price and reduces or removes the position | ✓ VERIFIED | Live sell-all via curl confirmed cash restored and position removed; `backend/tests/portfolio/test_service.py::TestExecuteTradeSell` (partial + full sell) both pass |
| 4 | Buying beyond cash / selling more than owned refused with a clear on-screen error, state unchanged | ✓ VERIFIED | `test_buy_costing_one_cent_more_than_balance_is_rejected`, `test_oversell_by_one_share_raises_insufficient_shares`, `test_rejected_sell_leaves_state_unchanged` all pass; live curl reproduced both 400s; `tradeErrorMessage()` renders the exact copy inline |
| 5 | Positions table shows ticker/qty/avg cost/price/unrealized P&L/%change; header total (cash+positions) moves with every price tick | ✓ VERIFIED | `PositionRow.tsx` renders all six fields (`grep` confirms `formatPrice`/`formatPercent` ×2, `numeric` ×5, `text-up\|text-down` ×2); `derivePortfolioValue`/`derivePositionRows` unit-tested against changing price maps; both wired via `useMemo` off the single SSE `prices` object in `page.tsx` |

**Score:** 5/5 ROADMAP success criteria verified (0 present-but-behavior-unverified)

### Detailed Plan-Level Must-Haves (36 truths across 3 plans)

All 36 `must_haves.truths` (13 in 02-01, 12 in 02-02, 11 in 02-03, including backstop items) were checked individually against the codebase and passing test/grep evidence. None failed. Representative/high-risk ones, verified directly:

| # | Truth (abbreviated) | Plan | Status | Evidence |
|---|---|---|---|---|
| 1 | Fill price read from `PriceCache.get`, request model carries no price field (D-01) | 02-01 | ✓ VERIFIED | `uv run python -c "...assert 'price' not in TradeRequest.model_fields"` → `ok`; `routes.py` `TradeRequest` has no price field |
| 2 | Untradable ticker refused before any write (D-02) | 02-01 | ✓ VERIFIED | `test_buy_of_untradable_ticker_raises_and_writes_nothing` pass; live curl `ZZZZ` buy → 400 `untradable_ticker` |
| 3 | Buy at cash boundary: exact cost succeeds → $0; $0.01 more rejected | 02-01 | ✓ VERIFIED | `test_buy_costing_exactly_cash_balance_succeeds_and_zeroes_cash`, `test_buy_costing_one_cent_more_than_balance_is_rejected` both pass |
| 4 | Every accepted trade appends exactly 1 `trades` row; no code path updates/deletes one (PORT-10) | 02-01/02-02 | ✓ VERIFIED | `grep -hEv '^\s*#' backend/app/portfolio/*.py \| grep -Eic 'update trades\|delete from trades'` → 0; `TestAppendOnlyTradeHistory` passes |
| 5 | `BEGIN IMMEDIATE` issued before first read | 02-01 | ✓ VERIFIED | `grep -c 'BEGIN IMMEDIATE' backend/app/portfolio/service.py` → 1; code shows it as first statement in the `try` block |
| 6 | Concurrent trades serialize — only one of two racing buys succeeds | 02-02 | ✓ VERIFIED (behavioral test) | `uv run pytest tests/portfolio/test_service.py -k concurrent -q` → 1 passed (threaded race test, not a sequential-call fake) |
| 7 | No string-built SQL anywhere in the package | 02-01/02-02 | ✓ VERIFIED | `grep -Ec '\.format\(\|f"[^"]*SELECT\|f"[^"]*INSERT\|f"[^"]*UPDATE\|%s'` → 0 |
| 8 | Sell of exactly all owned shares removes the `positions` row entirely | 02-02 | ✓ VERIFIED | `test_selling_all_shares_removes_position_row` pass; live curl confirmed empty `positions: []` after full sell |
| 9 | Selling 11 of 10 owned raises `InsufficientSharesError` reporting `owned: 10` | 02-02 | ✓ VERIFIED | `test_oversell_by_one_share_raises_insufficient_shares` pass |
| 10 | Inline error clears on next ticker/quantity change (D-04) | 02-02 | ✓ VERIFIED | `TradeBar.tsx` `handleTickerChange`/`handleQuantityChange` both call `setError(null)` |
| 11 | Buy/Sell disabled during in-flight request | 02-02 | ✓ VERIFIED | `canSubmit = validation.ok && !submitting`; both buttons `disabled={!canSubmit}` |
| 12 | `derivePositionRows` recomputes P&L/% from displayed price, not passed through from snapshot | 02-03 | ✓ VERIFIED | `frontend/lib/portfolio.ts` code + `frontend/lib/portfolio.test.ts` (8 dedicated cases: null-price, zero-cost, live-tick override, unheld ticker) |
| 13 | Sell to zero shares removes the row immediately, never a zero-quantity row | 02-03 | ✓ VERIFIED | Backend `DELETE FROM positions` on `new_quantity == 0`; live curl confirmed; no client-side filtering needed since server never returns the row |
| 14 | No rounding inside `portfolio.ts`; `formatPrice` truncates only at render | 02-01/02-03 | ✓ VERIFIED | `grep -Ec 'toFixed\|Math\.round' frontend/lib/portfolio.ts` → 0 |
| 15 | Failed `/api/portfolio` fetch keeps last-good snapshot, not null/zero | 02-01 | ✓ VERIFIED | `page.tsx` `fetchPortfolio().catch()` only logs, never calls `setPortfolio(null)` or clears state |

Remaining plan-level truths (empty-state copy, skeleton row counts, tabular-nums columns, watchlist-length ticker cap, backstop double-precision statements, etc.) were each individually checked via the grep/test gates in the plans' own `acceptance_criteria` blocks — see Behavioral Spot-Checks below for the full gate run. All passed with no exceptions found.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/portfolio/models.py` | `Position`, `TradeResult`, `TradeRejected` family | ✓ VERIFIED | All exports present; `InsufficientSharesError` raised by the sell branch |
| `backend/app/portfolio/service.py` | `execute_trade()`, `get_portfolio()` | ✓ VERIFIED | Both present, HTTP-agnostic, buy+sell branches, `BEGIN IMMEDIATE` |
| `backend/app/portfolio/routes.py` | `create_portfolio_router()`, `TradeRequest` | ✓ VERIFIED | Both endpoints registered, `TradeRejected`→400, `sqlite3.OperationalError`→503 |
| `backend/tests/portfolio/test_service.py` | Buy/sell/edge-case coverage | ✓ VERIFIED | 139 backend tests pass overall; portfolio subtree 26 tests pass |
| `frontend/lib/portfolio.ts` | `derivePortfolioValue`, `derivePositionRows` | ✓ VERIFIED | Both pure, no fetch/timer, both exported and unit-tested (15 assertions) |
| `frontend/lib/trade.ts` | `validateTradeInput`, `tradeErrorMessage`, `MALFORMED_INPUT_MESSAGE` | ✓ VERIFIED | All exported, exact UI-SPEC copy strings grep-confirmed, 12 unit assertions |
| `frontend/components/TradeBar.tsx` | Buy+Sell inputs/buttons | ✓ VERIFIED | Both actions wired to `/api/portfolio/trade`, disabled gating, inline error |
| `frontend/components/PositionsTable.tsx` / `PositionRow.tsx` | 6-column positions readout | ✓ VERIFIED | Skeleton/empty/populated states, `POSITION_ROW_GRID`, up/down coloring |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `backend/app/main.py` | `backend/app/portfolio/routes.py` | `app.include_router(create_portfolio_router(cache))` | ✓ WIRED | `grep -c 'create_portfolio_router(cache)' app/main.py` → 1; registered before `StaticFiles` mount |
| `backend/app/portfolio/service.py` | `backend/app/market/cache.py` | `cache.get(ticker)` | ✓ WIRED | `update = cache.get(ticker)` in `execute_trade`; live curl fill price (189.98) matched the watchlist's live AAPL price at fetch time |
| `frontend/components/TradeBar.tsx` | `backend/app/portfolio/routes.py` | `fetch POST /api/portfolio/trade` | ✓ WIRED | Live end-to-end curl reproduced the same contract the component posts |
| `frontend/app/page.tsx` | `frontend/lib/portfolio.ts` | `derivePortfolioValue`/`derivePositionRows` in `useMemo` | ✓ WIRED | Both called with the same `portfolio`/`prices` state; no second fetch or stream (`grep -Ec 'setInterval\|EventSource' page.tsx` → 0) |
| `frontend/components/TradeBar.tsx` | `frontend/lib/trade.ts` | `validateTradeInput`/`tradeErrorMessage` | ✓ WIRED | Both imported and called; error rendering path traced end to end |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `GET /api/portfolio` | `cash_balance`, `positions` | `users_profile`/`positions` SQLite tables via `db.connect()` | Yes — live curl against a real SQLite file returned real rows, not a static stub | ✓ FLOWING |
| `POST /api/portfolio/trade` | fill `price` | `PriceCache.get(ticker)` (populated by the running `MarketFeed`) | Yes — fill price matched the live simulator price at request time | ✓ FLOWING |
| `Header` cash/totalValue | `portfolio` state | `fetch('/api/portfolio')` + `usePriceStream()` prices | Yes — no hardcoded fallback found; null renders skeleton, not a static number | ✓ FLOWING |
| `PositionsTable` rows | `portfolio.positions` | Same `/api/portfolio` fetch, overlaid with SSE prices | Yes — verified live via curl (position appeared/disappeared correctly) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full backend suite | `cd backend && uv run --extra dev pytest -q` | 139 passed | ✓ PASS |
| Portfolio backend suite | `uv run --extra dev pytest tests/portfolio/ -q` | 26 passed | ✓ PASS |
| Ruff | `uv run ruff check app/ tests/` | All checks passed | ✓ PASS |
| Named test: oversell | `pytest tests/portfolio/test_service.py -k oversell -q` | 1 passed | ✓ PASS |
| Named test: concurrent race | `pytest tests/portfolio/test_service.py -k concurrent -q` | 1 passed | ✓ PASS |
| Named test: trade_history (append-only) | `pytest tests/portfolio/test_service.py -k trade_history -q` | 1 passed | ✓ PASS |
| Named test: total_value | `pytest tests/portfolio/test_service.py -k total_value -q` | 1 passed | ✓ PASS |
| D-01 structural check | `python -c "...TradeRequest.model_fields..."` | `ok` | ✓ PASS |
| Frontend unit suite | `npm test -- --run` | 60 passed (5 files) | ✓ PASS |
| Frontend lint | `npm run lint` | clean | ✓ PASS |
| Frontend build | `npx next build --webpack` | Compiled successfully, static pages generated | ✓ PASS |
| Live HTTP smoke: fresh portfolio | `curl GET /api/portfolio` | `cash_balance: 10000.0`, empty positions | ✓ PASS |
| Live HTTP smoke: buy | `curl POST /api/portfolio/trade {AAPL,buy,5}` | Filled at 189.98, cash → 9050.10 | ✓ PASS |
| Live HTTP smoke: oversell | `curl POST ... {AAPL,sell,9999}` | 400 `insufficient_shares`, owned 5.0 | ✓ PASS |
| Live HTTP smoke: untradable | `curl POST ... {ZZZZ,buy,1}` | 400 `untradable_ticker` | ✓ PASS |
| Live HTTP smoke: sell-all | `curl POST ... {AAPL,sell,5}` | Filled, cash → 10000.0, position removed | ✓ PASS |

All ~30 acceptance-criteria grep gates from the three plans (D-01/D-02 structural checks, SQL-injection guards, append-only guards, brand-color exclusions, pure-module guards, copy-string exactness) were individually re-run in this session and passed; see command transcript above for the representative set.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PORT-01 | 02-01 | $10,000 starting cash | ✓ SATISFIED | Live curl fresh-DB `cash_balance: 10000.0`; Header renders it |
| PORT-02 | 02-01 | Buy at market price, instant, no confirm/fees | ✓ SATISFIED | Live curl buy; no dialog component in TradeBar |
| PORT-03 | 02-02 | Sell at market price, instant | ✓ SATISFIED | Live curl sell; `TestExecuteTradeSell` |
| PORT-04 | 02-01/02-02 | Insufficient-cash buy rejected with clear error | ✓ SATISFIED | Unit tests + `tradeErrorMessage` copy |
| PORT-05 | 02-02 | Overselling rejected with clear error | ✓ SATISFIED | Unit tests + live curl 400 |
| PORT-06 | 02-03 | Positions table: 6 columns | ✓ SATISFIED | `PositionRow.tsx` renders all 6; grep-confirmed |
| PORT-07 | 02-01/02-03 | Live total value in header; positions move live | ✓ SATISFIED | `derivePortfolioValue`/`derivePositionRows` unit-tested, wired via `useMemo` |
| PORT-10 | 02-01/02-02 | Append-only trade history | ✓ SATISFIED | grep gate (0 UPDATE/DELETE on `trades`) + `TestAppendOnlyTradeHistory` |
| UI-03 | 02-01/02-02 | Trade bar: ticker/qty, one-click buy/sell | ✓ SATISFIED | `TradeBar.tsx` Buy+Sell buttons, single click, disabled gating |
| TEST-01 | 02-02 | Backend unit tests: trade execution, P&L math, edge cases | ✓ SATISFIED | 26 portfolio tests incl. concurrency race; 139 total backend tests pass |

No orphaned requirements: the phase's declared requirement set (PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, PORT-10, UI-03, TEST-01) exactly matches REQUIREMENTS.md's Phase 2 traceability rows, and every ID appears in at least one plan's `requirements:` frontmatter (02-01: PORT-01/02/04/07/10/UI-03; 02-02: PORT-03/04/05/UI-03/TEST-01; 02-03: PORT-06/07).

**Documentation note (non-blocking):** REQUIREMENTS.md's checkbox list shows PORT-06/PORT-07 already checked `[x]` (committed by Plan 02-03 at `fd116d8`) while PORT-01–05/10/UI-03/TEST-01 remain `[ ]` despite being implemented by Plans 02-01/02-02. This is a partial documentation update, not a code gap — worth a follow-up `docs` commit to check the remaining boxes, but does not affect the phase goal.

### Anti-Patterns Found

None. Scanned every file this phase created or modified (`backend/app/portfolio/*.py`, `frontend/lib/portfolio.ts`, `frontend/lib/trade.ts`, `frontend/components/TradeBar.tsx`, `frontend/components/Header.tsx`, `frontend/components/PositionRow.tsx`, `frontend/components/PositionsTable.tsx`, `frontend/app/page.tsx`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/"not yet implemented" — zero matches (excluding the `placeholder=` JSX prop, which is legitimate input UX, not a debt marker).

### Prohibitions (judgment-tier — flagged for human review)

Per `must_haves.prohibitions` and the verification-overrides prohibition-routing rule, all 5 prohibitions across the three plans are `verification: judgment`. This agent's read is a non-authoritative LLM-judge pass, not a substitute for human sign-off:

| # | Prohibition | Plan | LLM-judge read | Flag |
|---|---|---|---|---|
| 1 | MUST NOT silently partial-fill or substitute a different quantity | 02-01 | Code always either fills the exact requested quantity or raises a `TradeRejected` subclass — no partial-fill code path found | Human review recommended |
| 2 | MUST NOT present simulated money as real | 02-01 | `page.tsx` shows a persistent disclaimer: "Prices shown are generated by a market simulator, not live exchange data." | Human review recommended |
| 3 | MUST NOT use shaming/blaming language in rejections | 02-02 | Reviewed all three error sentences in `trade.ts` — state fact + limit only, no characterization found | Human review recommended |
| 4 | MUST NOT use urgency/dark-pattern framing in the trade bar | 02-02 | No pre-filled quantity, no countdown, no scarcity copy found in `TradeBar.tsx` | Human review recommended |
| 5 | MUST NOT present a stale price as live without the user being able to tell | 02-03 | P&L always recomputed from the same price actually displayed (live tick or snapshot fallback) — cannot disagree by construction | Human review recommended |

None of these look violated on inspection, but per the fail-closed protocol for judgment-tier prohibitions, they are surfaced as a human-verification item rather than silently marked passed.

### Human Verification Required

See frontmatter `human_verification` — 3 harvested end-of-phase UI checks (deferred from `<human-check>` blocks on `auto`-type tasks per `config.json`'s `human_verify_mode: end-of-phase`) plus 1 consolidated prohibitions-review item. All 4 require a running browser and are not resolvable by this agent's static/automated evidence gathering.

### Gaps Summary

No gaps found. Every ROADMAP success criterion, every plan-level must-have truth, every declared artifact, and every key link is present, substantive, and wired, with passing automated tests (139 backend + 60 frontend) and a live end-to-end HTTP smoke test performed in this verification session (fresh portfolio → buy → oversell rejection → untradable rejection → sell-all → position removed). The only open items are visual/interactive confirmations that a live browser session must supply, and the standard human sign-off on judgment-tier prohibitions — both routed to human verification, not to gaps.

---

_Verified: 2026-08-16T06:15:33Z_
_Verifier: Claude (gsd-verifier)_
