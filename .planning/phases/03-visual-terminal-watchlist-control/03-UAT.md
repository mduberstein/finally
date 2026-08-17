---
status: testing
phase: 03-visual-terminal-watchlist-control
source: [03-VERIFICATION.md]
started: 2026-08-17T14:50:00Z
updated: 2026-08-17T14:50:00Z
---

## Current Test

number: 1
name: POST a new ticker (e.g. PYPL) via the live add form and wait ~2s
expected: |
  Row appears immediately with an em-dash/null price, then shows a live streaming price within one poll interval; posting the same ticker again shows the duplicate error inline
awaiting: user response

## Tests

### 1. POST a new ticker (e.g. PYPL) via the live add form and wait ~2s
expected: Row appears immediately with an em-dash/null price, then shows a live streaming price within one poll interval; posting the same ticker again shows the duplicate error inline
result: [pending]

### 2. Type an invalid ticker (e.g. aa1) into the add form
expected: Add button stays disabled and no request is sent
result: [pending]

### 3. Click the remove (x) control on a watchlist row, then re-add the same ticker
expected: Row disappears immediately; re-adding starts its sparkline empty rather than resuming its old shape; portfolio/cash/positions unaffected by a watchlist removal
result: [pending]

### 4. Load the app against a fresh database and watch the Portfolio Value panel without trading
expected: Empty state, then a chart appears with a new point roughly every 30 seconds
result: [pending]

### 5. Buy shares, confirm the P&L chart gets an immediate point, buy again later and confirm two points join into a line, reload and confirm both persist
expected: Chart updates immediately on trade and on the 30s cadence, survives reload
result: [pending]

### 6. Buy a large position and two smaller ones; observe the heatmap
expected: Rectangle sizes are visibly proportional to position weight; losing positions render red, winning ones green, each with a signed percent label
result: [pending]

### 7. Click AAPL then GOOGL rows in the watchlist; click the remove control on a row
expected: Main chart switches instantly with no loading flicker on ticker click; remove control does not also select/switch the chart
result: [pending]

### 8. Confirm the AI Copilot placeholder panel visually matches the height/chrome of the heatmap and P&L chart
expected: Same panel treatment, no interactive elements
result: [pending]

### 9. Open the app maximized on a wide screen, then narrow to ~800px, then widen back
expected: All eight panels visible without horizontal scroll at wide width; single stacked column with nothing hidden at ~800px; charts redraw (not blank) at both widths; removing all watchlist tickers doesn't shift the rest of the layout
result: [pending]

### 10. Full desktop layout — watchlist column padding/alignment, no clipping in any of the five row columns
expected: Ticker, price, percent, sparkline, and remove control all render without clipping at the 420px column width
result: [pending]

## Summary

total: 10
passed: 0
issues: 0
pending: 10
skipped: 0
blocked: 0

## Gaps
