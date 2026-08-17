---
phase: quick-260817-mlm
plan: 01
subsystem: backend-portfolio
tags: [bugfix, tdd, float-precision, portfolio]
status: complete
dependency-graph:
  requires: []
  provides:
    - "_QUANTITY_EPSILON threshold in app/portfolio/service.py"
  affects:
    - "backend/app/portfolio/service.py (_apply_sell close-position branch)"
tech-stack:
  added: []
  patterns:
    - "Epsilon-threshold float comparison replacing exact equality for position-close detection"
key-files:
  created: []
  modified:
    - backend/app/portfolio/service.py
    - backend/tests/portfolio/test_service.py
decisions:
  - "One-sided comparison (new_quantity <= _QUANTITY_EPSILON) with no abs() — execute_trade's quantity > owned guard makes a negative new_quantity unreachable, so a symmetric abs() check would be defensive code for an unreachable state"
  - "Epsilon set to 1e-9 — economically indistinguishable from zero (worth < $0.00001 even at a $10,000 share price) while orders of magnitude above the ~1e-17 float noise it absorbs and orders of magnitude below any plausible fractional trade quantity"
metrics:
  duration: "~10 minutes"
  completed: "2026-08-17"
actuals:
  tokens: 4500
  tasks: 2
  commits: 2
---

# Phase quick-260817-mlm Plan 01: Fix `_apply_sell`'s exact-float-0 close-position check Summary

Replaced an exact `== 0` float equality check in `_apply_sell` with a `<= 1e-9` epsilon threshold, so a fractional sell that fully closes a fractional position (e.g., three `0.1` buys accumulating to `0.30000000000000004`, then a `0.3` sell) deletes the `positions` row instead of leaving a permanent ~1e-17 ghost row.

## What Was Built

- **Task 1 (RED, tracer)**: Added `test_fractional_sell_leaving_float_residual_removes_position_row`, which reproduces the exact scenario from WR-02 (`03-REVIEW.md`) — three `0.1` buys, then a `0.3` sell — and confirmed it fails against the unfixed code with the predicted residual (`5.551115123125783e-17`). Also added `test_remainder_far_above_epsilon_keeps_the_position_row`, pinning the non-deletion boundary at `1e-7` (100x the epsilon), which passed both before and after the fix.
- **Task 2 (GREEN)**: Added module-level `_QUANTITY_EPSILON = 1e-9` constant with a rationale docstring, and changed `_apply_sell`'s close-position branch from `new_quantity == 0` to `new_quantity <= _QUANTITY_EPSILON`. Extended `_apply_sell`'s docstring to explain why the one-sided comparison (no `abs()`) is safe: `execute_trade`'s own oversell guard (`quantity > owned` raises before `_apply_sell` is reached) makes a negative `new_quantity` unreachable.

## Verification

- `cd backend && uv run --extra dev pytest -q` — 174 passed (172 prior + 2 new)
- `cd backend && uv run --extra dev pytest tests/portfolio/test_service.py -q` — 25 passed
- `cd backend && uv run --extra dev ruff check app/ tests/` — all checks passed
- `grep -c '_QUANTITY_EPSILON' app/portfolio/service.py` — 2 (declaration + use in `_apply_sell`)
- `git diff --stat` for the Task 2 commit — exactly one file changed (`app/portfolio/service.py`); `test_service.py` was already committed in Task 1

## Deviations from Plan

None — plan executed exactly as written. Precondition check passed (baseline `uv run --extra dev pytest -q` reported 172 passing tests before any edit). Task 1's RED state was confirmed with the exact predicted residual value before Task 2 touched any implementation code, per the design notes' "prove the bug is real" requirement.

## Known Stubs

None.

## Threat Flags

None — this change modifies an internal predicate on an already-authorized, already-validated sell path. No new input, query, or trust boundary is introduced. Full threat register documented in the plan's `<threat_model>` (T-mlm-01 through T-mlm-04), all dispositioned `mitigate` or `accept` and closed by this fix.

## Self-Check: PASSED

- FOUND: backend/app/portfolio/service.py
- FOUND: backend/tests/portfolio/test_service.py
- FOUND commit 68444ee (test: add failing regression test)
- FOUND commit b744353 (feat: epsilon threshold fix)
