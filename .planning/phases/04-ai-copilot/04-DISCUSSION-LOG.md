# Phase 4: AI Copilot - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 4-AI Copilot
**Areas discussed:** Chat panel UI & interactions, Assistant personality & tone, Fractional share trading via chat, Message history UX on reload

---

## Chat panel UI & interactions

### Transcript layout

| Option | Description | Selected |
|--------|-------------|----------|
| Chat bubbles | User/assistant messages as distinct rounded bubbles, aligned left/right | ✓ |
| Flat terminal log | Plain stacked text lines with a role prefix, no bubble chrome | |
| You decide | No strong preference | |

**User's choice:** Chat bubbles

### Message input placement

| Option | Description | Selected |
|--------|-------------|----------|
| Pinned at bottom | Input bar fixed at the bottom, transcript scrolls above | ✓ |
| Pinned at top | Input at the top, newest messages push down below it | |
| You decide | No strong preference | |

**User's choice:** Pinned at bottom

### Loading indicator

| Option | Description | Selected |
|--------|-------------|----------|
| Typing-dots animation | Animated ••• in place of the assistant's next message bubble | ✓ |
| Skeleton placeholder | Gray skeleton-text block, matching PnlChart's loading state | |
| You decide | No strong preference | |

**User's choice:** Typing-dots animation

### Executed action display

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct action card | Small bordered card beneath the message, e.g. "✓ Bought 5 AAPL @ $190.23" | ✓ |
| Inline prose only | Assistant describes the action in normal message text, no separate treatment | |
| You decide | No strong preference | |

**User's choice:** Distinct action card

---

## Assistant personality & tone

### Voice

| Option | Description | Selected |
|--------|-------------|----------|
| Terse terminal operator | Short, data-first sentences, minimal hedging | ✓ |
| Friendly advisor | Warmer, more conversational, fuller explanations | |
| You decide | No strong preference | |

**User's choice:** Terse terminal operator

### Declined-trade phrasing

| Option | Description | Selected |
|--------|-------------|----------|
| Direct + numeric | States the exact shortfall, e.g. "Can't buy 50 TSLA — that's $12,450 but you have $8,200 cash." | ✓ |
| Softer + suggestion | Explains the block and offers an alternative | |
| You decide | No strong preference | |

**User's choice:** Direct + numeric

### Proactivity

| Option | Description | Selected |
|--------|-------------|----------|
| Reactive only | Only acts/analyzes when the user asks or explicitly agrees in the same turn | ✓ |
| Proactively suggests | Can volunteer trade ideas or watchlist additions unprompted | |
| You decide | No strong preference | |

**User's choice:** Reactive only

### Hedging/disclaimers

| Option | Description | Selected |
|--------|-------------|----------|
| None — it's simulated money | No "this isn't financial advice" disclaimers anywhere | ✓ |
| Light disclaimer on first message | One-time note in the first assistant response | |
| You decide | No strong preference | |

**User's choice:** None — it's simulated money

---

## Fractional share trading via chat

| Option | Description | Selected |
|--------|-------------|----------|
| Whole shares only | Consistent with the manual trade bar; schema/execute_trade() stay float-ready for later | ✓ |
| Allow fractional (dollar-amount buys) | Lets the assistant do "buy $500 of AAPL" style requests | |
| You decide | No strong preference | |

**User's choice:** Whole shares only
**Notes:** User initially interrupted this line of questioning to revisit an earlier point, then clarified they wanted to proceed to the next area (Message history UX) rather than change any prior answer — no decisions were altered.

---

## Message history UX on reload

### History load scope

| Option | Description | Selected |
|--------|-------------|----------|
| Load full history, capped | Full persisted conversation, capped at a reasonable count (e.g. last 100 messages) | ✓ |
| Load everything, no cap | Entire chat_messages history with no limit | |
| You decide | No strong preference | |

**User's choice:** Load full history, capped

### Scroll position on load

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom, newest message | Auto-scrolls to the most recent message on load | ✓ |
| Top, oldest message | Starts at the beginning of history | |
| You decide | No strong preference | |

**User's choice:** Bottom, newest message

### Session divider

| Option | Description | Selected |
|--------|-------------|----------|
| No divider | Restored history and new messages render identically | ✓ |
| Show a divider | A subtle line/label marks where this page load's messages begin | |
| You decide | No strong preference | |

**User's choice:** No divider

---

## Claude's Discretion

- Exact action-card styling (border color, icon, spacing) within the dark-terminal theme
- Exact typing-dots animation implementation
- The precise history cap number (D-10 says "reasonable," e.g. 100)
- Whether failed-trade attempts get a distinct visual treatment or are prose-only (no action card, since nothing executed)

## Deferred Ideas

- Fractional/dollar-amount trades via chat ("buy $500 of AAPL") — schema and `execute_trade()` stay ready for it, not enabled this phase
- Proactive/unprompted trade suggestions — assistant stays reactive-only this phase
