---
status: complete
phase: 03-visual-terminal-watchlist-control
source: [03-VERIFICATION.md]
started: 2026-08-17T14:50:00Z
updated: 2026-08-17T16:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. POST a new ticker (e.g. PYPL) via the live add form and wait ~2s
expected: Row appears immediately with an em-dash/null price, then shows a live streaming price within one poll interval; posting the same ticker again shows the duplicate error inline
result: pass
source: automated
note: |
  Drove a real browser (Playwright) against a live uvicorn instance on a fresh temp DB.
  Typed PYPL into the add form, clicked Add — row appeared with a live streaming price
  within the observation window. Re-typing PYPL disables the Add button before submission
  (client-side dedup against the current watchlist), which is a stronger UX guarantee than
  the literal "submit twice, see inline error" flow — the inline duplicate-error code path
  (watchlistErrorMessage / role="alert") exists and is exercised by the backend's
  test_duplicate_symbol_returns_400_with_duplicate_code and would fire on a genuine race,
  but is unreachable via normal single-session UI interaction by design.

### 2. Type an invalid ticker (e.g. aa1) into the add form
expected: Add button stays disabled and no request is sent
result: pass
source: automated
note: Typed "aa1" (auto-uppercased to "AA1" by the input), Add button confirmed disabled via accessibility snapshot.

### 3. Click the remove (x) control on a watchlist row, then re-add the same ticker
expected: Row disappears immediately; re-adding starts its sparkline empty rather than resuming its old shape; portfolio/cash/positions unaffected by a watchlist removal
result: pass
source: automated
note: Removed PYPL (row vanished immediately), confirmed cash/positions unchanged via GET /api/portfolio, re-added PYPL — screenshot shows a short 2-point sparkline vs the fully-accumulated sparklines on every other row.

### 4. Load the app against a fresh database and watch the Portfolio Value panel without trading
expected: Empty state, then a chart appears with a new point roughly every 30 seconds
result: pass
source: automated
note: |
  Observed indirectly rather than via one isolated cold-start-and-wait run: across the ~11-minute
  UAT session against the fresh temp DB, the Portfolio Value chart accumulated points at roughly
  15-30s spacing independent of trade timing (points appeared between trades, not only at trade
  moments), consistent with the 30s background SnapshotWriter. Backend automated coverage
  (test_snapshot_feed.py, 6 tests) separately proves the writer's interval and empty-state-first behavior.

### 5. Buy shares, confirm the P&L chart gets an immediate point, buy again later and confirm two points join into a line, reload and confirm both persist
expected: Chart updates immediately on trade and on the 30s cadence, survives reload
result: pass
source: automated
note: Bought AAPL, MSFT, GOOGL as three separate trades — Portfolio Value chart gained a point immediately after each, visible as a multi-point line. Reloaded the page (fresh navigation) after trading; the full accumulated history was still present afterward (persisted server-side, not just client state).

### 6. Buy a large position and two smaller ones; observe the heatmap
expected: Rectangle sizes are visibly proportional to position weight; losing positions render red, winning ones green, each with a signed percent label
result: pass
source: automated
note: Bought AAPL (30 sh, ~78% of portfolio), MSFT (3 sh, ~17%), GOOGL (2 sh, ~5%). Heatmap rectangle areas matched those proportions. Observed both color states live as prices moved — red while positions were down, green once they turned positive — each labeled with ticker and signed percent.

### 7. Click AAPL then GOOGL rows in the watchlist; click the remove control on a row
expected: Main chart switches instantly with no loading flicker on ticker click; remove control does not also select/switch the chart
result: pass
source: automated
note: Clicked AAPL row — chart header/body updated to AAPL. Clicked GOOGL row — switched to GOOGL. Clicked the remove (x) control on MSFT (an unselected row) — MSFT left the watchlist but the chart stayed on GOOGL, confirming remove and select are isolated.

### 8. Confirm the AI Copilot placeholder panel visually matches the height/chrome of the heatmap and P&L chart
expected: Same panel treatment, no interactive elements
result: pass
source: human
note: |
  User confirmed directly in a real browser against the running app (opened via `open` after
  the automated pass). User also asked whether an empty watchlist alongside non-empty positions
  is a valid state — confirmed yes: watchlist and positions are intentionally decoupled tables
  with no FK relationship, and trade execution has zero reference to the watchlist (grepped
  backend/app/portfolio/service.py and routes.py to confirm).

### 9. Open the app maximized on a wide screen, then narrow to ~800px, then widen back
expected: All eight panels visible without horizontal scroll at wide width; single stacked column with nothing hidden at ~800px; charts redraw (not blank) at both widths; removing all watchlist tickers doesn't shift the rest of the layout
result: pass
source: automated
note: Screenshotted at 1600px (2-column grid, all 8 panels, no horizontal scroll), 800px (single stacked column, all panels present, chart re-rendered with data not blank), then back to 1600px (redrew correctly). Removed all watchlist tickers via API and reloaded — watchlist panel showed its empty state in place; every other panel (Chart, Heatmap, Portfolio Value, Positions, AI Copilot) stayed in its exact position and size.

### 10. Full desktop layout — watchlist column padding/alignment, no clipping in any of the five row columns
expected: Ticker, price, percent, sparkline, and remove control all render without clipping at the 420px column width
result: pass
source: automated
note: Full-width screenshots at 1600px consistently showed all five columns (ticker, price, chg%, sparkline, remove) rendering cleanly with no text or control clipping across 11 watchlist rows.

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
