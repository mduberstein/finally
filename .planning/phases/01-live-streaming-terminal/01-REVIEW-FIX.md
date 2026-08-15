---
phase: 01-live-streaming-terminal
fixed_at: 2026-08-15T02:30:00Z
review_path: .planning/phases/01-live-streaming-terminal/01-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-08-15T02:30:00Z
**Source review:** `.planning/phases/01-live-streaming-terminal/01-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (fix_scope: critical_warning — 1 critical + 5 warnings)
- Fixed: 6
- Skipped: 0

**Verification environment:** All backend fixes verified in the isolated worktree
(`.claude/worktrees/rf-01-50144-1786760049`, since torn down) with `uv run --extra
dev pytest` (10/10 backend tests passing after all fixes). Frontend fixes verified
via Tier 1 (re-read + structural check) and grep for stale call-site signatures,
because the worktree has no `node_modules` installed (by design — worktrees are
dependency-free); `npx tsc`/`vitest` were not run there. Frontend numbers are not
independently reproducible from the worktree post-teardown; re-run `npm run
typecheck` and `npx vitest run` in the main checkout to confirm.

## Fixed Issues

### CR-01: SQLite connections are never closed — `with connect() as conn:` leaks a file descriptor per call

**Files modified:** `backend/app/db/database.py`
**Commit:** `f9cad7a`
**Applied fix:** Wrapped both `initialize()`'s and `watchlist_tickers()`'s connection
usage in `contextlib.closing()` so `conn.close()` always runs, in addition to the
existing commit/rollback behavior of `with conn:`. Verified with `python3 -c "import ast..."`
syntax check and `uv run pytest tests/test_db.py` (6/6 passing).

### WR-01: Blocking SQLite I/O runs directly on the event loop in an async route

**Files modified:** `backend/app/main.py`
**Commit:** `c1d3dcd`
**Applied fix:** `GET /api/watchlist` now calls `db.watchlist_tickers` via
`starlette.concurrency.run_in_threadpool` instead of synchronously on the event
loop, matching the reviewer's suggested fix exactly. Verified with `uv run pytest
tests/test_app.py` (4/4 passing).

### WR-02: Watchlist seed order depends on wall-clock timestamp ties, undermining the "in add order" contract

**Files modified:** `backend/app/db/database.py`
**Commit:** `d5d8125`
**Applied fix:** Changed `watchlist_tickers()`'s `ORDER BY added_at, ticker` to
`ORDER BY rowid`, relying on SQLite's monotonic insertion-order rowid instead of
timestamp equality (the `watchlist` table has an implicit rowid — it is not
declared `WITHOUT ROWID` and its `id` column is `TEXT`, not `INTEGER PRIMARY KEY`).
This also naturally preserves add-order for future `POST /api/watchlist` inserts.
Verified with `uv run pytest tests/test_db.py tests/test_app.py` (10/10 passing,
including `test_fresh_init_seeds_ten_watchlist_rows_in_order`).

### WR-03: Unsafe type assertion fabricates a partial `PriceTick`

**Files modified:** `frontend/lib/flash.ts`, `frontend/components/PriceCell.tsx`, `frontend/lib/flash.test.ts`
**Commit:** `51f4a52`
**Applied fix:** Narrowed `nextFlashState`'s second parameter from `tick: PriceTick`
to `direction: PriceTick["direction"]`, removing the `const tick = { direction } as
PriceTick` cast in `PriceCell.tsx` entirely — the call site now passes `direction`
directly. Also updated `flash.test.ts`, whose existing tests called
`nextFlashState(prev, tick(direction), now)` with full fabricated `PriceTick`
objects; those calls now pass the direction string directly, matching the new
signature (this file was not named in the REVIEW.md Fix section but requires the
same signature change to remain valid — a necessary consequence of the fix, not
scope creep). Verified via Tier 1 re-read and `grep -rn "nextFlashState"` confirming
no remaining call sites use the old three-arg-object signature. No `node_modules`
in the isolated worktree, so `vitest`/`tsc` were not run — re-verify with `npx
vitest run lib/flash.test.ts` in the main checkout.

### WR-04: SSE payloads are parsed and cast without runtime validation or error handling

**Files modified:** `frontend/lib/usePriceStream.ts`
**Commit:** `0397064`
**Applied fix:** Wrapped `JSON.parse(event.data) as PriceTick` in a try/catch;
on parse failure, dispatches `reduceConnection(state, { kind: "error" }, ...)`
(a variant already used by `source.onerror`, confirmed valid via
`lib/connection.ts`'s `ConnectionEvent` union) and returns without touching
`prices` state, matching the reviewer's suggested fix. Verified via Tier 1
re-read; no `node_modules` available for `tsc` in the worktree.

### WR-05: Watchlist fetch failure is indistinguishable from a genuinely empty watchlist

**Files modified:** `frontend/app/page.tsx`
**Commit:** `f552b05`
**Applied fix:** Added a `response.ok` check that throws before `.json()` parsing,
and the `.catch()` handler now `console.error`s the failure before falling back to
`setWatchlist([])`. Deliberately did not add the reviewer's suggested
`watchlistError` state variable, since nothing in `Watchlist.tsx` consumes it —
introducing an unused state field would violate the project's "don't overengineer"
convention (`CLAUDE.md`) without changing runtime behavior; console logging plus
the `response.ok` check already resolves the core issue (failures are now
distinguishable via devtools console instead of silently rendering as "empty").
Verified via Tier 1 re-read.

## Skipped Issues

None — all 6 in-scope findings were fixed.

---

_Fixed: 2026-08-15T02:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
