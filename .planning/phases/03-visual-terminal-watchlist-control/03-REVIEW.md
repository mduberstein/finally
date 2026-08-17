---
phase: 03-visual-terminal-watchlist-control
reviewed: 2026-08-17T14:31:47Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - backend/app/main.py
  - backend/app/portfolio/__init__.py
  - backend/app/portfolio/routes.py
  - backend/app/portfolio/service.py
  - backend/app/portfolio/snapshot_feed.py
  - backend/app/watchlist/__init__.py
  - backend/app/watchlist/models.py
  - backend/app/watchlist/routes.py
  - backend/app/watchlist/service.py
  - backend/tests/portfolio/test_routes.py
  - backend/tests/portfolio/test_service.py
  - backend/tests/portfolio/test_snapshot_feed.py
  - backend/tests/watchlist/__init__.py
  - backend/tests/watchlist/test_routes.py
  - backend/tests/watchlist/test_service.py
  - frontend/app/page.tsx
  - frontend/components/ChatPlaceholder.tsx
  - frontend/components/Heatmap.tsx
  - frontend/components/HeatmapCell.tsx
  - frontend/components/MainChart.tsx
  - frontend/components/PnlChart.tsx
  - frontend/components/Sparkline.tsx
  - frontend/components/Watchlist.tsx
  - frontend/components/WatchlistAddForm.tsx
  - frontend/components/WatchlistRow.tsx
  - frontend/lib/heatmap.test.ts
  - frontend/lib/heatmap.ts
  - frontend/lib/portfolio.ts
  - frontend/lib/priceHistory.test.ts
  - frontend/lib/priceHistory.ts
  - frontend/lib/types.ts
  - frontend/lib/usePriceHistory.ts
  - frontend/lib/watchlistForm.test.ts
  - frontend/lib/watchlistForm.ts
  - frontend/package-lock.json
  - frontend/package.json
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-08-17T14:31:47Z
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

Reviewed the portfolio and watchlist backend modules (routes, services, snapshot feed, tests) and the frontend watchlist/heatmap/chart layer (components, hooks, pure derivation libraries, tests) introduced for this phase. Overall the backend trade/snapshot logic is careful about atomicity (`BEGIN IMMEDIATE` around the cash race, append-only trade history, no synthesized snapshot data) and the frontend derivation libraries (`heatmap.ts`, `priceHistory.ts`, `portfolio.ts`) are pure, well-tested, and consistent with the backend's own P&L formulas.

No critical/blocker-level defects were found (no injection vectors, no hardcoded secrets, no unsafe eval/exec, parameterized SQL throughout). Three warning-level issues were found: an inconsistent concurrency guard between the trade path and the watchlist-cap path, a float-equality bug in position closing that is latent today but will misbehave once fractional trades (explicitly planned for Phase 4) are wired in, and a frontend state bug where the selected ticker is never invalidated after its watchlist entry is removed, leaving a frozen, no-longer-live price displayed in the main chart header. Four info-level quality items are also listed below.

## Warnings

### WR-01: `add_ticker`'s cap check and insert are not atomic, unlike the equivalent cash-balance race in `execute_trade`

**File:** `backend/app/watchlist/service.py:43-59`
**Issue:** `add_ticker` reads the current watchlist count with a plain `SELECT COUNT(*)`, then performs the `INSERT` as a separate statement, committing at the end. Nothing pins these two statements into one write transaction the way `execute_trade` deliberately does with `conn.execute("BEGIN IMMEDIATE")` (`backend/app/portfolio/service.py:54`) specifically to close the analogous cash-balance TOCTOU race (and which the concurrency test `TestConcurrentTrades` in `backend/tests/portfolio/test_service.py:260-291` exists to prove). Two concurrent `add_ticker` calls that each read a count of 49 before either inserts can both pass the `>= MAX_WATCHLIST_TICKERS` check and both succeed, pushing the watchlist above its documented 50-ticker cap. Low real-world impact (single-user app, soft cap), but it's an inconsistency between two otherwise-parallel code paths that were clearly written with the race in mind for one of them.
**Fix:**
```python
with closing(connect()) as conn:
    conn.execute("BEGIN IMMEDIATE")
    try:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM watchlist WHERE user_id = ?",
            (DEFAULT_USER_ID,),
        ).fetchone()["n"]
        if count >= MAX_WATCHLIST_TICKERS:
            raise WatchlistFullError(MAX_WATCHLIST_TICKERS)
        try:
            conn.execute("INSERT OR ABORT INTO watchlist ...", (...))
        except sqlite3.IntegrityError as error:
            raise DuplicateTickerError(normalized) from error
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
```

### WR-02: `_apply_sell` closes a position with an exact float `== 0` check, which will misbehave for the fractional trades this module already anticipates

**File:** `backend/app/portfolio/service.py:248-265`
**Issue:** `new_quantity = position["quantity"] - quantity; if new_quantity == 0: DELETE ...`. `execute_trade`'s own docstring (lines 33-38) explains that `quantity` is typed `float` specifically because "Phase 4 adds fractional LLM-initiated trades" and callers will invoke `execute_trade` directly, bypassing `TradeRequest`'s integer constraint. Once that happens, a sell that should exactly zero out a fractional position (e.g. selling `2.5` of a `2.5`-share position built from several fractional buys) can leave `new_quantity` as a tiny nonzero float (`1e-15`-scale) due to binary floating-point subtraction, silently leaving a near-zero "ghost" position row instead of deleting it — `get_portfolio` would then show a position with a near-invisible but nonzero quantity forever. Today this is unreachable because the only caller (`TradeRequest.quantity: int = Field(gt=0)`) only ever passes whole-number floats, so it's dormant rather than actively wrong, but it's a real correctness gap in code that explicitly documents the future caller it needs to support.
**Fix:**
```python
_QUANTITY_EPSILON = 1e-9

def _apply_sell(...):
    new_quantity = position["quantity"] - quantity
    if new_quantity <= _QUANTITY_EPSILON:
        conn.execute("DELETE FROM positions WHERE id = ?", (position["id"],))
        return
    ...
```

### WR-03: `selectedTicker` is never cleared or invalidated when its watchlist entry is removed, leaving `MainChart` showing a frozen, no-longer-live price

**File:** `frontend/app/page.tsx:98-102, 108-122`
**Issue:** `handleRemove` (lines 108-122) updates `watchlist` state on success but never touches `selectedTicker`. `usePriceHistory`'s prune effect (`frontend/lib/usePriceHistory.ts:26-29`, driven by `pruneToWatchlist`) removes the ticker's accumulated points once it drops out of `watchlistTickers`, so `selectedPoints` becomes `[]` and `MainChart` falls back to its "select a ticker" body prompt (`frontend/components/MainChart.tsx:43`). However, `selectedPrice`/`selectedChangePercent` (page.tsx:99-102) are read straight from the `prices` map produced by `usePriceStream`, which is **never pruned** (`frontend/lib/usePriceStream.ts:30,47` only ever merges into the map, nothing ever deletes a key) and the backend's `MarketFeed` stops requesting quotes for a ticker once it's off the watchlist (`db.watchlist_tickers` is re-read each poll), so that entry simply stops receiving new ticks and freezes at its last value. The net effect: after removing the currently-selected ticker, `MainChart`'s header keeps showing that ticker's symbol, a price, and a change percent — all frozen at the moment of removal, with no indication to the user that it is stale and no longer tracked — while the chart body directly below says "Select a ticker from the watchlist."
**Fix:**
```tsx
async function handleRemove(ticker: string): Promise<boolean> {
  try {
    const response = await fetch(`/api/watchlist/${ticker}`, { method: "DELETE" });
    if (!response.ok) return false;
    const body = (await response.json()) as { removed: boolean };
    if (body.removed) {
      setWatchlist((current) => (current ?? []).filter((entry) => entry.ticker !== ticker));
      setSelectedTicker((current) => (current === ticker ? null : current));
    }
    return true;
  } catch {
    return false;
  }
}
```

## Info

### IN-01: `WatchlistRow` nests a real `<button>` inside a `role="button"` container

**File:** `frontend/components/WatchlistRow.tsx:38-72`
**Issue:** The row is a `div role="button" tabIndex={0}` with its own click/keydown handling for row selection, and it wraps a genuine `<Button>` (renders a native `<button>`) for ticker removal. `event.stopPropagation()` on the inner button prevents the double-fire in practice, but nesting an interactive native element inside another element carrying an interactive ARIA role is against the ARIA authoring rules and can confuse some screen readers' "clickable region" heuristics.
**Fix:** Consider making the row a plain container (`div`, no `role="button"`) with the ticker/price cells wrapped in their own `button`/link for selection, keeping the remove control as a true sibling rather than a nested interactive descendant.

### IN-02: `shadcn` CLI package is listed as a runtime `dependency`, not a `devDependency`

**File:** `frontend/package.json:12-24`
**Issue:** `shadcn` (`^4.18.0`) only ships a CLI binary (`package-lock.json:9599` shows `"bin": {"shadcn": "dist/index.js"}`) and is not imported anywhere in `frontend/` source. It belongs in `devDependencies` alongside `eslint`/`typescript`/`vitest`, not `dependencies`, which currently implies it's needed at runtime.
**Fix:** Move `"shadcn": "^4.18.0"` from `dependencies` to `devDependencies` in `frontend/package.json`.

### IN-03: Module-level `PriceCache` singleton in `main.py` is shared across the whole test session, not just one app lifespan

**File:** `backend/app/main.py:19, 26-36`
**Issue:** `cache = PriceCache()` is created once at import time, and every router factory (`create_stream_router`, `create_portfolio_router`, `create_watchlist_router`) is bound to that single instance at import. Each `with TestClient(app)` block in the test suite re-runs `lifespan()` (spinning up a fresh `MarketFeed`/`SnapshotWriter` against a fresh per-test SQLite file), but all of them write into the *same* long-lived `cache` object for the life of the pytest process. Tests currently happen to be safe because every test reseeds the same 10 default tickers, but this is an implicit coupling: a future test that watches a non-default ticker, or that asserts on `cache.snapshot()` being empty/fresh at the start of a test, will observe leftover state from a previous test's feed.
**Fix:** Not necessarily worth restructuring for production (the singleton is required there — the stream router must bind before the app/lifespan exists), but consider exposing a `cache.clear()` test-only hook, or resetting `app.state.prices` per test via a fixture, to make the coupling explicit rather than incidental.

### IN-04: `delete_watchlist_ticker` re-derives the normalized ticker instead of reusing `remove_ticker`'s result

**File:** `backend/app/watchlist/routes.py:44-50`
**Issue:** The route computes `ticker.strip().upper()` inline for the response body after already calling `remove_ticker(ticker)`, which internally calls `normalize_ticker` and performs the identical strip/upper. The normalization logic is duplicated across two call sites for what should be a single source of truth.
**Fix:** Have `remove_ticker` return the normalized ticker string alongside the boolean (e.g. a small `tuple[str, bool]` or a dataclass), the way `add_ticker` already returns the normalized ticker, so the route doesn't need to re-derive it.

---

_Reviewed: 2026-08-17T14:31:47Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
