---
phase: quick-260817-mlm
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/portfolio/service.py
  - backend/tests/portfolio/test_service.py
autonomous: true
requirements: [WR-02]

estimate:
  tokens: 18000
  raw_tokens: 18000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - A sell that fully closes a fractional position built from repeated fractional buys deletes the `positions` row, even when binary float subtraction leaves a ~1e-17 residual instead of exactly 0.0.
    - "`get_portfolio` reports no entry at all for a ticker closed that way — no near-invisible ghost position with a 1e-17 quantity."
    - A sell leaving a genuinely small remainder (1e-7 shares, 100x the epsilon) still keeps the position row with that quantity intact — the threshold is not over-eager.
    - Existing whole-share buy/sell/close behavior is unchanged; all 172 existing backend tests still pass.
  artifacts:
    - backend/app/portfolio/service.py
    - backend/tests/portfolio/test_service.py
  key_links:
    - "`_QUANTITY_EPSILON` in `backend/app/portfolio/service.py` gates the DELETE branch of `_apply_sell`, which is the only code path that removes a `positions` row"
    - "`execute_trade`'s `quantity > owned` guard (service.py:66-68) runs before `_apply_sell`, guaranteeing `new_quantity` is never negative — which is why a one-sided comparison is sufficient and an abs() is not needed"
---

<objective>
Fix WR-02 from `.planning/phases/03-visual-terminal-watchlist-control/03-REVIEW.md`: `_apply_sell` (`backend/app/portfolio/service.py:248-265`) decides whether to delete a position row using an exact float equality check against zero. `execute_trade`'s own docstring (service.py:33-38) states that `quantity` is typed `float` precisely because Phase 4 adds fractional LLM-initiated trades that call this function directly, bypassing `TradeRequest`'s integer constraint. Once that lands, a sell that should exactly close a fractional position leaves a ~1e-17 residual from binary float subtraction, the delete branch is skipped, and a permanent ghost position row with a near-invisible nonzero quantity survives in `positions` and in every `get_portfolio` response.

Verified today: three buys of `0.1` accumulate to `0.30000000000000004`; selling `0.3` passes the `quantity > owned` guard and leaves `5.551115123125783e-17` behind.

Purpose: Close a dormant correctness gap in the exact code path Phase 4 is about to start calling, before Phase 4 builds on top of it. A ghost row silently corrupts positions display, heatmap sizing, and every `total_value` snapshot from that point forward.

Output: A `_QUANTITY_EPSILON` threshold in `backend/app/portfolio/service.py` replacing the exact-zero delete condition, plus two regression tests in `backend/tests/portfolio/test_service.py`.
</objective>

<execution_context>
@/Users/mdub/SOFT-DEV/GitHubRepos/AIProjects/finally/.claude/gsd-core/workflows/execute-plan.md
@/Users/mdub/SOFT-DEV/GitHubRepos/AIProjects/finally/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/03-visual-terminal-watchlist-control/03-REVIEW.md

@backend/app/portfolio/service.py
@backend/tests/portfolio/test_service.py
</context>

<design_notes>
**Why a one-sided threshold rather than an abs() comparison.** `execute_trade` raises `InsufficientSharesError` whenever `quantity > owned` (service.py:66-68), so `_apply_sell` is only ever reached with `quantity <= owned`. IEEE 754 subtraction of `a - b` where `a >= b` always yields a non-negative result, so `new_quantity` is provably never negative. A symmetric `abs(new_quantity) <= EPSILON` would add a branch for an unreachable state — defensive code with no reachable caller. Use the one-sided form and document the guard that makes it safe.

**Why 1e-9.** Quantities are share counts. 1e-9 shares of even a $10,000 stock is worth $0.00001 — economically indistinguishable from zero, and orders of magnitude above the ~1e-17 float noise this is designed to absorb, while orders of magnitude below any fractional quantity an LLM would plausibly emit. Task 1's second test pins the non-deletion boundary at 1e-7 (100x the threshold) so an over-eager future widening of the epsilon fails loudly.

**Scope boundary — do NOT expand.** Three adjacent things are deliberately out of scope:
1. The `quantity > owned` oversell guard has its own float-boundary behavior (selling `0.3` against an owned `0.29999999999999993` raises). That is a separate question about what "sell everything" should mean, it is not WR-02, and Phase 4 will decide it when it designs the LLM sell path.
2. `TradeRequest.quantity: int = Field(gt=0)` in the route layer stays an integer for this phase. Phase 4 relaxes it, not this fix.
3. `_position_entry`'s `avg_cost != 0` check (service.py:189) is a divide-by-zero guard, not a close-position decision. Leave it alone.

**Order matters.** Task 1 writes tests against the *unfixed* code and confirms the ghost-row test genuinely fails. This proves the bug is real rather than assumed, per the project's debugging rule. Do not apply the fix until that RED state is observed.
</design_notes>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Prove the ghost row with a failing regression test</name>
  <files>backend/tests/portfolio/test_service.py</files>
  <precondition>`uv run` must be invoked from `backend/`, not the repo root, and the `dev` extra must be requested explicitly (`uv run --extra dev pytest`) — a plain `uv run pytest` silently resolves to a system pytest without `pytest-asyncio` and the suite misbehaves. Halt if the baseline `uv run --extra dev pytest -q` does not report 172 passing tests before any edit.</precondition>
  <behavior>
    Two new tests, both added to the existing `TestExecuteTradeSell` class in `backend/tests/portfolio/test_service.py`:

    - `test_fractional_sell_leaving_float_residual_removes_position_row` — RED before the fix, GREEN after.
      Setup: cache AAPL at 190.0, then three separate `execute_trade("AAPL", "buy", 0.1, cache)` calls.
      Evidence assertion: read `quantity` straight from the `positions` table and assert it is strictly greater than 0.3 — this proves the accumulated holding is 0.30000000000000004, so the subsequent sell of 0.3 passes the oversell guard and leaves a positive residual.
      Act: `execute_trade("AAPL", "sell", 0.3, cache)`.
      Assert: `get_portfolio(cache)["positions"]` is empty, AND a direct `SELECT * FROM positions` returns zero rows.

    - `test_remainder_far_above_epsilon_keeps_the_position_row` — GREEN both before and after the fix; it exists to pin the threshold's upper boundary.
      Setup: cache AAPL at 190.0, `execute_trade("AAPL", "buy", 0.5, cache)`.
      Act: `execute_trade("AAPL", "sell", 0.4999999, cache)`.
      Assert: exactly one position remains, with `quantity == pytest.approx(1e-7)` — a remainder 100x the threshold survives untouched.
  </behavior>
  <action>
    Add both tests described in `&lt;behavior&gt;` to the `TestExecuteTradeSell` class in `backend/tests/portfolio/test_service.py`, placed immediately after the existing `test_selling_all_shares_removes_position_row` so the whole-share case and the fractional case read together.

    Follow the file's established conventions exactly: `(self, tmp_path, monkeypatch)` signature, `_use_tmp_db(tmp_path, monkeypatch)` as the first line, `cache = PriceCache()` then `cache.apply([_quote("AAPL", 190.0)])`, `pytest.approx` for every float equality, and `with database.connect() as conn:` for direct table reads. Import nothing new — `database`, `PriceCache`, `_quote`, `execute_trade`, `get_portfolio`, and `pytest` are all already imported at the top of the file.

    Call `execute_trade` directly with fractional quantities. This is the whole point: it is the exact Phase 4 entry path the function's docstring anticipates, and it bypasses the route's integer constraint without needing any route change.

    Give the first test a docstring naming WR-02 and stating the observed residual value (5.551115123125783e-17) so a future reader knows the scenario is measured rather than hypothetical.

    Then run the suite and CONFIRM the first test FAILS and the second test PASSES. Do not touch `app/portfolio/service.py` in this task. If the first test passes against the unfixed code, the scenario is wrong — fix the scenario until it reproduces the ghost row, do not proceed to Task 2.
  </action>
  <verify>
    <automated>cd backend &amp;&amp; ! uv run --extra dev pytest tests/portfolio/test_service.py -q -k "float_residual"</automated>
    <automated>cd backend &amp;&amp; uv run --extra dev pytest tests/portfolio/test_service.py -q -k "far_above_epsilon"</automated>
  </verify>
  <done>`test_fractional_sell_leaving_float_residual_removes_position_row` fails against the current unfixed `_apply_sell`, and `test_remainder_far_above_epsilon_keeps_the_position_row` passes. `app/portfolio/service.py` is unmodified.</done>
</task>

<task type="auto">
  <name>Task 2: Replace the exact-zero close check with an epsilon threshold</name>
  <files>backend/app/portfolio/service.py</files>
  <action>
    In `backend/app/portfolio/service.py`, declare a module-level constant `_QUANTITY_EPSILON = 1e-9` alongside the existing `SNAPSHOT_HISTORY_LIMIT` near the top of the file, following the same style: the constant, then a docstring string literal directly beneath it. That docstring must state (a) that share quantities below this threshold are treated as a closed position, (b) that this absorbs the ~1e-17 float subtraction residue left when a fractional sell fully closes a fractional holding, and (c) that 1e-9 shares is economically zero even at a four-figure share price.

    Then change the close-position branch in `_apply_sell` so the DELETE fires when `new_quantity` is at or below `_QUANTITY_EPSILON` instead of when it is precisely zero. Use the one-sided comparison `new_quantity <= _QUANTITY_EPSILON`; do NOT wrap it in `abs()`. Extend `_apply_sell`'s existing docstring with a sentence explaining that `execute_trade`'s oversell guard makes a negative `new_quantity` unreachable, which is what licenses the one-sided form — a future reader must be able to see why no absolute value is needed.

    Change nothing else in the function: the early `return` after the DELETE, the `avg_cost`-untouched comment, and the UPDATE branch all stay exactly as they are. Do not touch `execute_trade`'s oversell guard, `_position_entry`, or the route's `TradeRequest` model — see the scope boundary in `&lt;design_notes&gt;`.

    Then run the full backend gate. Both Task 1 tests must now pass and every pre-existing test must stay green. If an existing test fails, this fix is wrong — do not edit the existing test to accommodate it.
  </action>
  <verify>
    <automated>cd backend &amp;&amp; uv run --extra dev pytest tests/portfolio/test_service.py -q</automated>
    <automated>cd backend &amp;&amp; uv run --extra dev pytest -q</automated>
    <automated>cd backend &amp;&amp; uv run --extra dev ruff check app/ tests/</automated>
    <automated>cd backend &amp;&amp; grep -c '_QUANTITY_EPSILON' app/portfolio/service.py</automated>
  </verify>
  <done>The full backend suite reports 174 passing tests (172 prior + 2 new), `ruff check app/ tests/` is clean, and `_QUANTITY_EPSILON` appears at least twice in `app/portfolio/service.py` (its declaration and its use in `_apply_sell`).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| trade request → `positions` table | No new boundary crossed. This changes only the internal predicate deciding whether an already-authorized, already-validated sell deletes or updates a row. No new input is accepted, no new query is issued, and the transaction envelope in `execute_trade` is untouched. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-mlm-01 | Tampering | `_apply_sell` position-row lifecycle | low | mitigate | This plan IS the mitigation. A surviving ghost row misrepresents the user's holdings to `get_portfolio`, the positions table, the heatmap's weight sizing, and every subsequent `total_value` snapshot — a data-integrity defect in the system of record for what the user owns. |
| T-mlm-02 | Denial of Service | unbounded ghost-row accumulation in `positions` | low | mitigate | Without the fix, every fractional round-trip through a Phase 4 LLM-initiated trade can leave one permanent undeletable row; repeated agentic trading accumulates them without bound, and `_positions_value` iterates all of them on every snapshot. The epsilon delete removes the accumulation mechanism entirely. |
| T-mlm-03 | Tampering | `_QUANTITY_EPSILON` silently discarding real shares | low | accept | The threshold can in principle delete a genuinely-held sub-1e-9-share position. That holding is worth under $0.00001 even at a $10,000 share price, and the second regression test pins the non-deletion boundary 100x above the threshold so any future widening of the epsilon fails the suite rather than silently eating value. |
| T-mlm-04 | Repudiation | `trades` audit log | low | accept | Unaffected. `_insert_trade` still appends one row per accepted sell regardless of which `_apply_sell` branch runs, so the append-only trade history remains a complete record of what was executed. Covered by the existing `test_every_accepted_sell_appends_one_trade_row`. |

No package-manager install tasks are introduced by this plan (no new Python dependencies), so the supply-chain threat class does not apply.
</threat_model>

<verification>
- `cd backend && uv run --extra dev pytest -q` — full backend suite green, count 172 → 174
- `cd backend && uv run --extra dev pytest tests/portfolio/test_service.py -q` — portfolio service tests all green
- `cd backend && uv run --extra dev ruff check app/ tests/` — no lint errors
- `cd backend && grep -n '_QUANTITY_EPSILON' app/portfolio/service.py` — constant declared with a docstring and referenced inside `_apply_sell`
- `cd backend && git diff --stat` — exactly two files changed: `app/portfolio/service.py` and `tests/portfolio/test_service.py`
</verification>

<success_criteria>
- A fractional sell that fully closes a fractional position deletes the `positions` row despite a ~1e-17 float residual
- `get_portfolio` returns no entry for a ticker closed that way
- A remainder of 1e-7 shares — 100x the threshold — still keeps its position row intact
- Whole-share trade behavior is byte-for-byte unchanged; no pre-existing test was modified
- The oversell guard, the route's integer quantity constraint, and `_position_entry` are all untouched
- WR-02 in `.planning/phases/03-visual-terminal-watchlist-control/03-REVIEW.md` is closed, leaving WR-01 as the only open warning from that review
</success_criteria>

<output>
Create `.planning/quick/260817-mlm-fix-apply-sell-s-exact-float-0-close-pos/260817-mlm-SUMMARY.md` when done
</output>
