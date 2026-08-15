---
status: testing
phase: 01-live-streaming-terminal
source: [01-VERIFICATION.md]
started: 2026-08-15T02:40:00.000Z
updated: 2026-08-15T02:40:00.000Z
---

## Current Test

number: 1
name: Ten-row live watchlist on first paint
expected: |
  Ten skeleton rows appear briefly before real data lands, then the populated
  grid shows AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX with
  prices in a wide, prominent, non-jittering column.
awaiting: user response

## Tests

### 1. Ten-row live watchlist on first paint
expected: Build the export, copy `frontend/out` to `backend/static`, run uvicorn on port 8000, open `http://localhost:8000`. Ten skeleton rows appear briefly before real data lands, then the populated grid shows AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX with prices in a wide, prominent, non-jittering column.
result: [pending]

### 2. Price flash tint and fade timing
expected: Watch the live watchlist grid for ~30 seconds. Price cells tint green on an uptick and red on a downtick, each tint fades back within roughly half a second, rows that are not moving show no tint, and every row always shows a direction triangle plus a signed percent.
result: [pending]

### 3. Reduced-motion suppression
expected: Set the OS to reduce motion, reload the page, and watch the grid. Tints stop animating; the direction glyph and signed percent still convey movement.
result: [pending]

### 4. Row hover/selection/focus affordances
expected: Hover and click a watchlist row, then tab to it with the keyboard. Accent-blue left-border stripe appears on hover and selection; a visible accent focus ring appears on keyboard focus.
result: [pending]

### 5. Connection indicator live resilience cycle
expected: With the app running and served through FastAPI, confirm the dot is green/Connected. Stop the uvicorn process and watch the dot go yellow then red with the label Disconnected, while watchlist rows keep showing their last prices rather than blanking. Restart uvicorn without touching the browser and confirm the dot returns to green on its own and prices resume.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
