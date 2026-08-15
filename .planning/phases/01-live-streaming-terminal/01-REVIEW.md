---
phase: 01-live-streaming-terminal
reviewed: 2026-08-14T00:00:00Z
depth: standard
files_reviewed: 30
files_reviewed_list:
  - .gitignore
  - backend/.gitignore
  - backend/app/db/__init__.py
  - backend/app/db/database.py
  - backend/app/db/schema.sql
  - backend/app/main.py
  - backend/tests/test_app.py
  - backend/tests/test_db.py
  - db/.gitkeep
  - frontend/app/globals.css
  - frontend/app/layout.tsx
  - frontend/app/page.tsx
  - frontend/components.json
  - frontend/components/ConnectionIndicator.tsx
  - frontend/components/Header.tsx
  - frontend/components/PriceCell.tsx
  - frontend/components/Watchlist.tsx
  - frontend/components/WatchlistRow.tsx
  - frontend/components/ui/skeleton.tsx
  - frontend/lib/connection.test.ts
  - frontend/lib/connection.ts
  - frontend/lib/flash.test.ts
  - frontend/lib/flash.ts
  - frontend/lib/format.test.ts
  - frontend/lib/format.ts
  - frontend/lib/types.ts
  - frontend/lib/usePriceStream.ts
  - frontend/next.config.ts
  - frontend/package.json
  - frontend/vitest.config.ts
findings:
  critical: 1
  warning: 5
  info: 0
  total: 6
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 30 (`frontend/package-lock.json` excluded as a lockfile per review scope rules)
**Status:** issues_found

## Summary

Reviewed the backend SQLite persistence layer, the FastAPI app shell, and the frontend watchlist/price-streaming stack (connection reducer, flash-tint reducer, formatting helpers, `usePriceStream`, and the presentational components). The unit-tested pure reducers (`connection.ts`, `flash.ts`, `format.ts`) are solid and well covered.

The standout defect is a genuine resource leak: `backend/app/db/database.py`'s `connect()` helper is used via `with connect() as conn:`, but Python's `sqlite3.Connection` context manager only commits/rolls back a transaction — it does **not** close the connection. This was verified empirically (see below). Because `watchlist_tickers()` uses this pattern and is polled continuously by the market feed and on every `GET /api/watchlist` request, the process leaks one open SQLite file handle roughly every poll cycle, for the life of the process — an eventual "too many open files" crash.

Several secondary issues in async/DB handling, seed-order determinism, and a couple of frontend type-safety/error-handling gaps round out the findings below.

## Critical Issues

### CR-01: SQLite connections are never closed — `with connect() as conn:` leaks a file descriptor per call

**File:** `backend/app/db/database.py:74` (`initialize()`) and `backend/app/db/database.py:102` (`watchlist_tickers()`)
**Issue:**
`connect()` returns a plain `sqlite3.Connection`. Both `initialize()` and `watchlist_tickers()` use it as `with connect() as conn: ...`. Python's `sqlite3.Connection.__exit__` only commits (or rolls back on exception) — it does **not** call `close()`. The connection, and its underlying OS file descriptor, stays open indefinitely.

Verified directly:
```
$ python3 -c "
import sqlite3, tempfile
path = tempfile.mktemp()
def connect():
    return sqlite3.connect(path)
c = connect()
with c as conn:
    pass
conn.execute('SELECT 1')   # succeeds — connection is still usable/open
print('CONNECTION STILL OPEN AFTER WITH BLOCK')
"
CONNECTION STILL OPEN AFTER WITH BLOCK
```

`watchlist_tickers()` is documented as "re-read on every poll" by `MarketFeed` (~500ms cadence per `planning/PLAN.md` §6) and is also called synchronously on every `GET /api/watchlist` request in `backend/app/main.py:47`. At ~2 leaked connections/second this exhausts a typical `ulimit -n` (1024–4096) within minutes to hours of the app running, after which every subsequent DB call (and likely the whole process) starts failing with `OSError: [Errno 24] Too many open files`. This is a data-loss/crash risk in an app whose core value proposition is a long-running live price stream.

**Fix:**
```python
from contextlib import closing

def initialize() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as conn, conn:
        conn.executescript(_SCHEMA_PATH.read_text())
        _seed_user_profile(conn)
        _seed_watchlist(conn)


def watchlist_tickers() -> list[str]:
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, ticker",
            (DEFAULT_USER_ID,),
        ).fetchall()
    return [row["ticker"] for row in rows]
```
`closing()` guarantees `conn.close()` runs; nesting `with conn:` (or calling `conn.commit()` explicitly, as `initialize()` already does) still handles the transaction. Any future callers of `connect()` should follow the same pattern — consider making this the enforced convention (e.g. a `with contextlib.closing(connect()) as conn:` helper, or a context manager wrapper around `connect()` itself) so the mistake can't recur as more DB code is added in later phases.

## Warnings

### WR-01: Blocking SQLite I/O runs directly on the event loop in an async route

**File:** `backend/app/main.py:44-50`
**Issue:** `async def watchlist()` calls `db.watchlist_tickers()` synchronously. `sqlite3` is a blocking library; every call does disk I/O on the single asyncio event loop thread. Because the same loop is responsible for pushing SSE price frames at the ~500ms cadence promised in `planning/PLAN.md` §6, any concurrent watchlist request (or the feed's own poll — not in this file's scope, but it calls the same `db.watchlist_tickers` callable) stalls price delivery to every connected SSE client for the duration of the disk read.
**Fix:** Run the blocking call off the loop, e.g.:
```python
from starlette.concurrency import run_in_threadpool

@app.get("/api/watchlist")
async def watchlist() -> list[dict]:
    tickers = await run_in_threadpool(db.watchlist_tickers)
    return [_watchlist_entry(ticker, cache.get(ticker)) for ticker in tickers]
```

### WR-02: Watchlist seed order depends on wall-clock timestamp ties, undermining the "in add order" contract

**File:** `backend/app/db/database.py:88-93` (`_seed_watchlist`) and `96-107` (`watchlist_tickers`)
**Issue:** `_seed_watchlist` inserts the ten default tickers in a tight loop, calling `_now_iso()` (`datetime.now(UTC).isoformat()`) separately for each row. `watchlist_tickers()` then orders by `added_at, ticker`. On any system/container where the wall clock's effective resolution is coarser than the loop's execution time (common in virtualized CI, and on some platforms even natively), several/all of the ten `added_at` values collide, and the secondary sort key (`ticker`, alphabetical) takes over — producing `AAPL, AMZN, GOOGL, JPM, META, MSFT, NFLX, NVDA, TSLA, V` instead of the intended seed order `AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX`. This directly contradicts the `watchlist_tickers()` docstring ("Tickers on the default user's watchlist, in add order") and risks flaking `backend/tests/test_app.py::TestWatchlist::test_returns_ten_default_tickers` and `backend/tests/test_db.py::TestInitialize::test_fresh_init_seeds_ten_watchlist_rows_in_order` on such systems.
**Fix:** Don't rely on timestamp equality-prone ordering for seed data. Either omit the `ORDER BY` and rely on SQLite's default rowid (insertion) order, or add an explicit monotonic sequence column and order by that:
```sql
ALTER TABLE watchlist ADD COLUMN seq INTEGER; -- or use rowid directly
```
```python
"SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY rowid"
```

### WR-03: Unsafe type assertion fabricates a partial `PriceTick`

**File:** `frontend/components/PriceCell.tsx:37`
**Issue:** `const tick = { direction } as PriceTick;` casts an object containing only `direction` to the full `PriceTick` interface (which also requires `ticker`, `price`, `previous_price`, `change`, `change_percent`, `timestamp`). This works today only because `nextFlashState` happens to read solely `tick.direction`. Any future change to `nextFlashState` (or a refactor that trusts the `PriceTick` type) will silently read `undefined` for the missing fields with no compiler warning, because the `as` cast has already suppressed the type checker.
**Fix:** Narrow the function's parameter type instead of lying about the object's shape:
```ts
// flash.ts
export function nextFlashState(
  prev: FlashState | null,
  direction: PriceTick["direction"],
  now: number,
): FlashState | null {
  if (direction === "flat") return prev;
  return { direction, startedAt: now };
}
```
```tsx
// PriceCell.tsx
setFlash((prev) => nextFlashState(prev, direction, Date.now()));
```

### WR-04: SSE payloads are parsed and cast without runtime validation or error handling

**File:** `frontend/lib/usePriceStream.ts:39-43`
**Issue:** `JSON.parse(event.data) as PriceTick` trusts the backend payload completely. Two failure modes are unhandled:
1. If `event.data` is not valid JSON, `JSON.parse` throws inside the `addEventListener("price", ...)` callback. The exception is not caught anywhere in this file, so it surfaces only as an uncaught error in the browser console; the tick is silently dropped and no connection-state event is dispatched, so `ConnectionIndicator` keeps reporting "Connected" even though a malformed frame just occurred.
2. If the JSON is valid but missing/mistyped fields (e.g. a future backend change), the `as PriceTick` cast happily lets `undefined`/wrong-typed values flow into `formatPrice`/`formatPercent`/`directionGlyph`, rendering `NaN` or `—` without any diagnostic.
**Fix:**
```ts
source.addEventListener("price", (event: MessageEvent<string>) => {
  let tick: PriceTick;
  try {
    tick = JSON.parse(event.data) as PriceTick;
  } catch {
    setConnection((state) => reduceConnection(state, { kind: "error" }, Date.now()));
    return;
  }
  setPrices((current) => ({ ...current, [tick.ticker]: tick }));
  setConnection((state) => reduceConnection(state, { kind: "message" }, Date.now()));
});
```

### WR-05: Watchlist fetch failure is indistinguishable from a genuinely empty watchlist

**File:** `frontend/app/page.tsx:14-19`
**Issue:** `.catch(() => setWatchlist([]))` swallows any fetch/network/parse failure and sets the same state as a real empty watchlist. `Watchlist.tsx` then renders "No tickers being tracked / Your watchlist will populate automatically when the app starts." — actively misleading a user whose backend is actually unreachable or erroring, and no failure is logged anywhere for debugging.
**Fix:** Track fetch failure as distinct state (or at minimum `console.error` the failure) so the UI/developer can tell "empty" apart from "failed to load":
```tsx
const [watchlistError, setWatchlistError] = useState(false);
useEffect(() => {
  fetch("/api/watchlist")
    .then((response) => {
      if (!response.ok) throw new Error(`watchlist fetch failed: ${response.status}`);
      return response.json();
    })
    .then((entries: WatchlistEntry[]) => setWatchlist(entries))
    .catch((error) => {
      console.error(error);
      setWatchlistError(true);
      setWatchlist([]);
    });
}, []);
```

---

_Reviewed: 2026-08-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
