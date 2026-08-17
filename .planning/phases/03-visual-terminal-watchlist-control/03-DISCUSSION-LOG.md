# Phase 3: Visual Terminal & Watchlist Control - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 03-visual-terminal-watchlist-control
**Areas discussed:** Charting library & approach, Chat panel placeholder, Watchlist add/remove UX, Tablet-width responsive strategy

---

## Charting library & approach

| Option | Description | Selected |
|--------|-------------|----------|
| Recharts | React-native declarative API, composes easily with the existing component style, good static-export compatibility. PLAN.md explicitly names it as an option. | ✓ |
| Lightweight Charts (TradingView) | Canvas-based, purpose-built for financial time series — the most "authentic trading terminal" look — but an imperative, less React-idiomatic API to wire up. | |

**User's choice:** Recharts
**Notes:** Heatmap will be a hand-built CSS grid regardless (matching Phase 1-2's precedent), not a dedicated treemap library — this was framed as part of the same question and not separately re-asked.

---

## Chat panel placeholder

| Option | Description | Selected |
|--------|-------------|----------|
| Reserve an empty placeholder panel now | Locks in the final grid proportions in Phase 3 so Phase 4 only fills content into an already-correctly-sized slot — avoids a Phase 4 layout reflow. | ✓ |
| Omit it, let Phase 4 add the panel | Phase 3's layout only accounts for the 7 non-chat panels; Phase 4 inserts an 8th panel and re-flows the grid then. | |

**User's choice:** Reserve an empty placeholder panel now
**Notes:** None

---

## Watchlist add/remove UX

| Option | Description | Selected |
|--------|-------------|----------|
| Inline text input + Add button in the watchlist panel | Type a ticker, press Add (or Enter); each row gets a small remove (×) control. Simple, no modal, consistent with the trade bar's plain-input pattern from Phase 2. | ✓ |
| Modal/dialog for adding tickers | Click an "Add ticker" button that opens a dialog with the input, confirm inside the dialog. More overhead, no dialog component exists yet in the codebase. | |

**User's choice:** Inline text input + Add button in the watchlist panel
**Notes:** None

---

## Tablet-width responsive strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Stack all panels vertically, scrollable | Every panel stacks in a single column; the page scrolls. Nothing is hidden — simplest correctness story for "usable, not broken." | ✓ |
| Collapse/hide secondary panels on tablet | Keep a denser desktop-like layout by hiding or collapsing less-critical panels at tablet width. | |

**User's choice:** Stack all panels vertically, scrollable
**Notes:** None

---

## Claude's Discretion

- Sparkline data-source/reset behavior on ticker removal-then-re-add — default to resetting sparkline history since there's no persisted price history to restore from.
- Main chart data granularity — follows the same client-side-accumulated-since-page-load pattern as sparklines; exact windowing/resolution left to judgment.
- Watchlist ticker validation and any practical maximum count — left to judgment.

## Deferred Ideas

- AI chat panel functionality — explicitly Phase 4, only the empty placeholder slot ships this phase.
- A dedicated treemap library for the heatmap — considered and explicitly declined in favor of a hand-built CSS grid.
