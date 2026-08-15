---
phase: 01-live-streaming-terminal
verified: 2026-08-15T02:35:00Z
status: human_needed
score: 2/4 must-haves verified
behavior_unverified: 2
overrides_applied: 0
behavior_unverified_items:
  - truth: "Prices update continuously without a page reload; each change briefly flashes green on an uptick or red on a downtick and fades back within about half a second"
    test: "Serve the static export through FastAPI, open the app in a browser, and watch the watchlist grid for ~30 seconds."
    expected: "Price cells tint green on an uptick and red on a downtick, the tint fades back to the panel background within roughly 500ms, an unchanged price shows no tint, and every row always shows a direction triangle plus a signed percent regardless of flash state. With the OS set to reduce motion, the tint stops animating but the glyph and percent remain."
    why_human: "The flash state machine (nextFlashState/isFlashActive/directionGlyph) is fully unit-tested (13/13 passing, time-injected, no fake timers needed) and the CSS keyframes/durations/prefers-reduced-motion rule are grep-confirmed in globals.css, but no test renders PriceCell in a browser and observes the actual tint-and-fade or the reduced-motion suppression — that is a rendering-layer, real-time visual behavior no unit test exercises."
  - truth: "The header connection dot reads green while the stream is healthy, yellow while reconnecting, and red when the stream is down — and recovers to green on its own after the backend comes back"
    test: "Serve the static export through FastAPI, confirm the dot is green/Connected, stop the uvicorn process and watch the dot go yellow then red, then restart uvicorn without touching the browser and confirm the dot returns to green automatically while watchlist rows keep their last known prices."
    expected: "Dot and label cycle Connected (green) -> Reconnecting (yellow) -> Disconnected (red) -> Connected (green) automatically, with no user action, and the watchlist grid never blanks during the outage."
    why_human: "The three-state reducer (reduceConnection) is fully unit-tested (11/11 passing, including the test-tier staleness-downgrade prohibition), and usePriceStream.ts is confirmed wired to real EventSource open/message/error events plus a periodic staleness tick. But the live EventSource retry/recovery behavior against an actually killed-and-restarted backend process, and the on-screen dot color transitions, require a live browser session and process control that no automated test in this repo exercises."
---

# Phase 1: Live Streaming Terminal Verification Report

**Phase Goal:** A user opens a browser and watches ten default tickers stream live prices in a dark trading terminal
**User Story (from PLAN.md, validated user-story format):** As a visitor opening FinAlly for the first time, I want to see ten default tickers streaming live prices in a dark trading terminal, so that I can watch the market move without reloading the page.
**Verified:** 2026-08-15T02:35:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## User Flow Coverage

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Open the app | `localhost:8000` serves a dark-themed page (`class="dark"` on `<html>`), no white flash | `frontend/app/layout.tsx` (dark class + Inter via next/font), `backend/app/main.py` static mount; confirmed live: `curl -sf http://127.0.0.1:8123/` returns `<html lang="en" class="dark ...">` | VERIFIED |
| See the watchlist | Grid lists AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX with prices | `frontend/components/Watchlist.tsx` + `WatchlistRow.tsx`; confirmed live: `GET /api/watchlist` returns exactly those 10 tickers with price data | VERIFIED |
| Watch prices move, flash | SSE pushes new prices twice a second; each change flashes green/red and fades in ~500ms | `frontend/lib/usePriceStream.ts` -> `/api/stream/prices` (confirmed live: two reads 4s apart differ for 6-7 of 10 tickers); flash tint/fade — see behavior_unverified_items | Data flow VERIFIED; visual flash PRESENT_BEHAVIOR_UNVERIFIED |
| Outcome: watch the market move without reloading | Whole page never reloads; connection dot honestly reflects stream health so a frozen screen is never mistaken for a quiet market | SSE `EventSource` confirmed open with no page navigation; connection reducer fully unit-tested — see behavior_unverified_items for the live recovery cycle | Data path VERIFIED; live resilience cycle PRESENT_BEHAVIOR_UNVERIFIED |

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — authoritative)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User visits `localhost:8000` and sees a dark terminal-style watchlist listing AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX with prices | VERIFIED | Live smoke test: built `frontend`, served via FastAPI on port 8123, `curl /` returns dark-classed HTML; `curl /api/watchlist` returns exactly the 10 tickers with prices; `frontend/app/globals.css` `.dark` block sets `#0d1117`/`#161b22`/`#30363d`/`#209dd7` (grep-confirmed) |
| 2 | Prices update continuously without a page reload; each change briefly flashes green on an uptick or red on a downtick and fades back within about half a second | PRESENT_BEHAVIOR_UNVERIFIED | Data path confirmed live (SSE stream changes over time); flash state machine and CSS keyframes present and unit-tested, but the rendered tint/fade is not exercised by any automated test — see behavior_unverified_items |
| 3 | The header connection dot reads green while the stream is healthy, yellow while reconnecting, and red when the stream is down — and recovers to green on its own after the backend comes back | PRESENT_BEHAVIOR_UNVERIFIED | Reducer fully unit-tested (11/11) including automatic recovery and staleness downgrade; wiring into `usePriceStream`/`ConnectionIndicator` confirmed by code read, but live kill/restart-against-a-browser behavior is unexercised — see behavior_unverified_items |
| 4 | Starting the app against an empty `db/` directory creates and seeds the database automatically; restarting against an existing one reuses it without wiping data | VERIFIED | Live test performed by this verifier: pointed `FINALLY_DB_PATH` at a fresh empty temp directory, started the app — `users_profile` seeded with `cash_balance=10000.0` and exactly 10 `watchlist` rows appeared; mutated `cash_balance` to `12345.67` via direct SQL, restarted the app — value and all 10 watchlist rows survived unchanged. `backend/tests/test_db.py` additionally covers the missing-table-recreated case (111/111 backend tests pass) |

**Score:** 2/4 truths verified (2 present + wired, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/db/schema.sql` | Six-table schema, all `CREATE TABLE IF NOT EXISTS` | VERIFIED | 6 tables confirmed by read: `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`, all `CREATE TABLE IF NOT EXISTS` |
| `backend/app/db/database.py` | Lazy init, additive seeding, watchlist reads; no fd leak | VERIFIED | `initialize()`/`watchlist_tickers()` both wrap connections in `contextlib.closing()` (CR-01 fix applied); live test confirmed 0 leaked `finally.db` file descriptors after 25 requests |
| `backend/app/main.py` | FastAPI app, lifespan feed wiring, REST routes, static mount | VERIFIED | `lifespan()` calls `db.initialize()`, constructs `MarketFeed(..., fallback_factory=SimulatorSource)`, calls `feed.start()` once, `await feed.stop()` on exit; `/api/watchlist` now uses `run_in_threadpool` (WR-01 fix applied) |
| `frontend/lib/usePriceStream.ts` | EventSource hook returning live prices + connection status | VERIFIED | Opens one `EventSource`, merges ticks by ticker (never replaces), feeds real `open`/`message`/`error` events plus a 2s staleness tick into `reduceConnection`; SSE JSON parse wrapped in try/catch (WR-04 fix applied) |
| `frontend/components/Watchlist.tsx` | Loading (10 skeletons), empty, and populated states | VERIFIED | `entries === null` -> 10 `Skeleton` rows; `entries.length === 0` -> "No tickers being tracked" / "Your watchlist will populate automatically when the app starts." (exact strings, grep-confirmed); populated -> one `WatchlistRow` per entry |
| `frontend/components/PriceCell.tsx` | Price + percent cell with flash tint and direction glyph | VERIFIED | Renders through `formatPrice`/`formatPercent`, drives tint via `nextFlashState`/keying on `startedAt`; glyph+percent always render independent of flash state; no `#209dd7` (accent) used for price movement (grep-confirmed 0) |
| `frontend/components/ConnectionIndicator.tsx` | Header dot + label reflecting stream health | VERIFIED | `role="status"` polite live region, dot color from `--up`/`--reconnecting`/`--down` semantic variables, visible label always one of the 3 fixed strings, `aria-describedby` carries the longer sentence only while disconnected |
| `frontend/lib/flash.ts` | Pure, time-injected flash state machine | VERIFIED | `FLASH_DURATION_MS=500`, `nextFlashState`/`isFlashActive`/`directionGlyph`; 0 internal `Date.now()`/`performance.now()` calls (grep-confirmed); 13/13 tests pass |
| `frontend/lib/connection.ts` | Pure, time-injected 3-state connection reducer | VERIFIED | `DISCONNECTED_AFTER_ERRORS=3`, `STALE_AFTER_MS=10000`; 0 internal clock reads (grep-confirmed); 11/11 tests pass, including the staleness-downgrade test-tier prohibition |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `backend/app/main.py` | `backend/app/market/feed.py` | `MarketFeed(create_source(), cache, db.watchlist_tickers, fallback_factory=SimulatorSource)` | WIRED | Confirmed by read; `fallback_factory=SimulatorSource` present exactly once |
| `backend/app/main.py` | `backend/app/market/stream.py` | `app.include_router(create_stream_router(cache))` | WIRED | Confirmed by read and live: `/api/stream/prices` emits parseable `price` frames |
| `backend/app/main.py` | `backend/app/db/database.py` | `lifespan` calls `db.initialize()`; watchlist route reads `db.watchlist_tickers()` | WIRED | Confirmed by read and live restart-safety test |
| `frontend/app/page.tsx` | `frontend/lib/usePriceStream.ts` | page renders live prices from the hook | WIRED | Confirmed by read: `usePriceStream()` called, `prices`/`status` passed down to `Watchlist`/`Header` |
| `frontend/lib/usePriceStream.ts` | `backend/app/market/stream.py` | `EventSource` opened against `/api/stream/prices` | WIRED | Confirmed live: SSE connection opens, delivers 10 named `price` events per cycle |
| `frontend/components/WatchlistRow.tsx` | `frontend/components/PriceCell.tsx` | row renders numeric cells through `PriceCell` | WIRED | Confirmed by read |
| `frontend/components/PriceCell.tsx` | `frontend/lib/flash.ts` | cell derives tint from `nextFlashState`/`isFlashActive` | WIRED | Confirmed by read |
| `frontend/lib/usePriceStream.ts` | `frontend/lib/connection.ts` | hook feeds EventSource events + tick into `reduceConnection` | WIRED | Confirmed by read |
| `frontend/components/Header.tsx` | `frontend/components/ConnectionIndicator.tsx` | header renders indicator in its right-hand slot | WIRED | Confirmed by read |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `/api/watchlist` response | `price`, `change_percent`, `direction` | `cache.get(ticker)` reading `PriceCache` written by `MarketFeed` polling `SimulatorSource` | Yes — live test: two reads 4s apart showed 6-7 of 10 ticker prices changed | FLOWING |
| `/api/stream/prices` SSE frames | same fields | same `PriceCache`, pushed every ~0.5s | Yes — live test: multiple distinct `price` events observed within a 4s window | FLOWING |
| `frontend` watchlist grid | `entries`, `prices` | `fetch('/api/watchlist')` + `usePriceStream()` merged in `Watchlist.tsx` | Yes — `live?.price ?? entry.price` prefers the SSE tick, confirmed by read | FLOWING |
| `db/finally.db` `users_profile.cash_balance` | seeded 10000.0, mutated 12345.67 | `initialize()` seed + direct SQL mutation | Yes — value survived a full app restart in this verifier's live test | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend test suite | `cd backend && uv run --extra dev pytest -q` | 111 passed, 1 warning (unrelated httpx deprecation notice) | PASS |
| Backend lint | `cd backend && uv run ruff check app/ tests/` | All checks passed | PASS |
| Frontend test suite | `cd frontend && npm test` | 3 test files, 33 tests, all passed (13 flash + 11 connection + 9 format) | PASS |
| Frontend lint | `cd frontend && npm run lint` | Clean, no output | PASS |
| Frontend build | `cd frontend && npm run build` | Compiled successfully, static pages generated (`frontend/out/index.html` exists) | PASS |
| Fresh empty `db/` seeds automatically | Live: pointed `FINALLY_DB_PATH` at an empty temp dir, started uvicorn, queried DB directly | `users_profile` seeded ($10,000.0), exactly 10 `watchlist` rows in `DEFAULT_TICKERS` | PASS |
| Restart preserves mutated data | Live: mutated `cash_balance` to 12345.67 via SQL, killed and restarted the app | `cash_balance` still 12345.67, 10 watchlist rows intact after restart | PASS |
| No SQLite fd leak (CR-01 regression check) | Live: 25 sequential `GET /api/watchlist` requests, checked `lsof -p <pid> | grep finally.db` | 0 open `finally.db` file descriptors held by the process at any point | PASS |
| `/api/health`, `/api/watchlist`, `/api/stream/prices`, `/` respond | Live curl smoke test against uvicorn serving the built static export | health `ok`; watchlist 10 entries; stream emits parseable `price` frames; `/` serves dark-classed HTML | PASS |
| Two watchlist reads 4s apart differ | Live curl, `sleep 4` between reads | 6-7 of 10 ticker prices changed between reads, proving the feed writes into the cache continuously | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| MARKET-01 | 01-01 | Watchlist prices update live via SSE from `PriceCache`/`MarketFeed` | SATISFIED | Live SSE test; `create_stream_router(cache)` wired in `main.py` |
| MARKET-02 | 01-03 | Prices flash green/red, fading over ~500ms | SATISFIED (data/logic); visual fade NEEDS HUMAN | `flash.ts` state machine + CSS keyframes present and unit-tested; live browser fade unexercised |
| MARKET-03 | 01-04 | Connection status indicator: green/yellow/red | SATISFIED (data/logic); live recovery cycle NEEDS HUMAN | `connection.ts` reducer + `ConnectionIndicator` wired; live kill/restart cycle unexercised |
| MARKET-04 | 01-01 | FastAPI starts `MarketFeed` with simulator on lifespan startup, stops cleanly | SATISFIED | `lifespan()` in `main.py`; `feed.start()` once, `await feed.stop()` on shutdown; `TestLifespan` passes |
| WATCH-01 | 01-01 | 10 default watchlist tickers on first launch | SATISFIED | Live test: fresh DB seeds exactly `AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX` |
| INFRA-01 | 01-01 | SQLite lazily initializes schema and seeds default data on first run | SATISFIED | Live test: fresh empty `db/` directory produces a fully seeded database on first start |
| UI-01 | 01-02 | Dark trading-terminal theme applied consistently | SATISFIED | `.dark` CSS block confirmed (`#0d1117`/`#161b22`/`#30363d`/`#209dd7`), no pure black, weights 400/600 only, `tabular-nums` present; live HTML confirmed `class="dark"` |

**Note (bookkeeping, not a functional gap):** `.planning/REQUIREMENTS.md` still shows all six of MARKET-01, MARKET-02, MARKET-04, WATCH-01, UI-01, and INFRA-01 as unchecked `[ ]` / "Pending" in its traceability table, while only MARKET-03 is marked `[x]` / "Complete" — even though this verification found all seven Phase 1 requirements functionally satisfied in the codebase. This looks like the same `gsd-tools.cjs query requirements.mark-complete` tooling failure the 01-04-SUMMARY.md already documented working around manually for MARKET-03 only; the other six were apparently never manually flipped. Recommend updating `.planning/REQUIREMENTS.md` to check off MARKET-01, MARKET-02, MARKET-04, WATCH-01, UI-01, and INFRA-01 before Phase 1 is considered closed, so the tracking file matches reality. This does not block phase sign-off since the underlying functionality is verified.

### Anti-Patterns Found

None. Scanned every file touched by this phase (`backend/app/db/*`, `backend/app/main.py`, and all `frontend/lib/*`, `frontend/components/*`, `frontend/app/*` files listed across the four plans' `files_modified`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers and empty-implementation patterns (`return null`, `return {}`, `return []`, `=> {}`) — zero matches. The one prior debt item (CR-01 SQLite fd leak) found by `01-REVIEW.md` was fixed in commit `f9cad7a` and independently re-confirmed live by this verifier (0 leaked fds after 25 requests).

### Human Verification Required

The pure logic behind both animated/dynamic truths is fully unit-tested and wired; what remains is browser-rendered, real-time visual/interaction confirmation that no automated test in this repo exercises.

### 1. Ten-row live watchlist on first paint

**Test:** Build the export, copy `frontend/out` to `backend/static`, run uvicorn on port 8000, open `http://localhost:8000`.
**Expected:** Ten skeleton rows appear briefly before real data lands, then the populated grid shows AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX with prices in a wide, prominent, non-jittering column.
**Why human:** Automated smoke test proves the underlying data path (10 tickers served, prices change over time), but the skeleton-to-populated transition and column stability are pixel-level rendering behavior.

### 2. Price flash tint and fade timing

**Test:** Watch the live watchlist grid for ~30 seconds.
**Expected:** Price cells tint green on an uptick and red on a downtick, each tint fades back within roughly half a second, rows that are not moving show no tint, and every row always shows a direction triangle plus a signed percent.
**Why human:** `flash.ts`'s state machine is fully unit-tested (13/13) and the CSS keyframes/durations are grep-confirmed, but the actual rendered tint-and-fade timing in a browser is not exercised by any automated test.

### 3. Reduced-motion suppression

**Test:** Set the OS to reduce motion, reload the page, and watch the grid.
**Expected:** Tints stop animating; the direction glyph and signed percent still convey movement.
**Why human:** Requires an OS-level accessibility setting and visual confirmation; the `prefers-reduced-motion` media query exists in the CSS (grep-confirmed) but is not exercised by a test.

### 4. Row hover/selection/focus affordances

**Test:** Hover and click a watchlist row, then tab to it with the keyboard.
**Expected:** Accent-blue left-border stripe appears on hover and selection; a visible accent focus ring appears on keyboard focus.
**Why human:** `hover:border-l-primary` / `focus-visible:border-l-primary` / `focus-visible:ring-ring` classes are present in `WatchlistRow.tsx` (confirmed by read) but not exercised by any automated interaction test.

### 5. Connection indicator live resilience cycle

**Test:** With the app running and served through FastAPI, confirm the dot is green/Connected. Stop the uvicorn process and watch the dot go yellow then red with the label Disconnected, while watchlist rows keep showing their last prices rather than blanking. Restart uvicorn without touching the browser and confirm the dot returns to green on its own and prices resume.
**Expected:** Dot and label cycle Connected -> Reconnecting -> Disconnected -> Connected automatically, with no user action, and the grid never blanks.
**Why human:** `reduceConnection` is fully unit-tested (11/11, including the staleness-downgrade prohibition), and the wiring into `usePriceStream`/`ConnectionIndicator` is confirmed by code read, but the live EventSource retry/recovery behavior against a killed-and-restarted backend process requires a live browser session and process control that no automated test exercises.

### Gaps Summary

No functional gaps found. All four ROADMAP success criteria have their underlying logic, wiring, and data flow independently verified live by this verifier (fresh-DB auto-seed, restart-safety, SSE streaming, dark theme, all 10 tickers, fd-leak regression check). The two truths involving continuous animation/live-process behavior (price flash fade timing, connection-dot live recovery cycle) have their pure state-machine logic fully unit-tested and their component wiring confirmed by code read, but the rendered visual behavior in a real browser against a real running/restarting backend is inherently outside what an automated verifier can exercise — both are routed to human verification rather than failed, consistent with the executors' own SUMMARY.md flags (01-03 D2, 01-04 D2) and the pre-approved handling for this phase. The one prior code-review finding (SQLite connection fd leak, critical) plus 5 warnings were all fixed (`01-REVIEW-FIX.md`) and independently re-confirmed by this verifier's own live regression test (0 leaked fds after 25 requests) and by a full backend+frontend test/lint/build pass (111/111 backend tests, 33/33 frontend tests, clean lint, clean build).

The only non-blocking issue found is a documentation bookkeeping gap: `.planning/REQUIREMENTS.md`'s checkboxes for MARKET-01, MARKET-02, MARKET-04, WATCH-01, UI-01, and INFRA-01 were never flipped to complete (only MARKET-03 was), even though this verification found all seven Phase 1 requirements functionally satisfied.

---

*Verified: 2026-08-15T02:35:00Z*
*Verifier: Claude (gsd-verifier)*
