# Phase 4: AI Copilot - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

A user can converse with an AI assistant that analyzes the portfolio (positions, cash, concentration, P&L) and acts on it — auto-executing trades and managing the watchlist — through natural language, with no confirmation dialogs. A loading indicator shows while the assistant thinks; declined trades come back as a plain-language explanation with the portfolio left unchanged; conversation history persists across page reloads; `LLM_MOCK=true` returns deterministic mock replies with no external API call.

</domain>

<decisions>
## Implementation Decisions

### Chat Panel UI & Interactions
- **D-01:** The transcript renders as chat bubbles (user/assistant, left/right aligned), not a flat terminal log. — **Reversibility:** reversible — isolated to the transcript component's rendering.
- **D-02:** The message input is pinned at the bottom of the chat panel, transcript scrolls above it — matches `TradeBar`'s existing fixed-input convention. — **Reversibility:** reversible.
- **D-03:** While waiting for a response, show an animated typing-dots indicator in place of the assistant's next message bubble. — **Reversibility:** reversible.
- **D-04:** An executed trade or watchlist change renders as a distinct bordered action card beneath the assistant's message (e.g. "✓ Bought 5 AAPL @ $190.23") — visually separated from prose so executed actions are unmistakable at a glance. — **Reversibility:** reversible.

### Assistant Personality & Tone
- **D-05:** Voice is terse/data-first — short sentences, leads with numbers, minimal hedging. Matches PLAN.md's "concise and data-driven" instruction and the Bloomberg-terminal aesthetic. — **Reversibility:** reversible — a system-prompt change.
- **D-06:** Declined trades (insufficient cash, overselling) are explained directly with exact numbers — e.g. "Can't buy 50 TSLA — that's $12,450 but you have $8,200 cash." Mirrors the trade bar's existing inline-error precedent. — **Reversibility:** reversible.
- **D-07:** The assistant is reactive only — it analyzes/trades/edits the watchlist when the user asks or explicitly agrees to a suggestion in the same turn. It does not volunteer trade ideas unprompted. Matches PLAN.md's "execute trades when the user asks or agrees." — **Reversibility:** reversible — a system-prompt/behavior constraint, not an architectural one.
- **D-08:** No financial-advice disclaimer language anywhere in responses — it's a $10k simulator with zero real-world stakes, so hedging would only add noise. — **Reversibility:** reversible.

### Trade Execution via Chat
- **D-09:** LLM-initiated trades stay whole-share only this phase, consistent with the manual trade bar (Phase 2 D-03). The assistant does not compute fractional quantities from dollar-amount requests (e.g. "buy $500 of AAPL"). `execute_trade()` and the `positions`/`trades` schema remain float-typed/ready for fractional trading to be enabled later without a migration. — **Reversibility:** reversible — a validation constraint on the LLM-facing trade schema, not a data-model change.

### Message History
- **D-10:** On page load, fetch the full persisted `chat_messages` history, capped at a reasonable count (e.g. last 100 messages) so a long-running conversation doesn't balloon the initial payload. — **Reversibility:** reversible.
- **D-11:** The transcript auto-scrolls to the newest message on load, matching how it will auto-scroll as new messages arrive during a live session. — **Reversibility:** reversible.
- **D-12:** No visual divider between restored prior history and this session's new messages — it's one continuous conversation with no session boundary that matters for a single-user app. — **Reversibility:** reversible.

### Claude's Discretion
- Exact action-card styling (border color, icon, spacing) within the dark-terminal theme and existing panel conventions.
- Exact typing-dots animation implementation (CSS vs. a small library-free component).
- The precise history cap number (D-10 says "reasonable," e.g. 100 — planner/executor can tune based on payload size).
- Whether failed-trade action cards (if any) get a distinct visual treatment from successful ones, or whether failures are prose-only (no action card) since nothing executed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Plan
- `planning/PLAN.md` §9 (LLM Integration — full request/response flow, structured output schema, auto-execution rules, system prompt guidance, mock mode behavior) — authoritative for the chat flow shape
- `planning/PLAN.md` §8 (API Endpoints — `POST /api/chat`) — endpoint contract
- `.planning/REQUIREMENTS.md` (CHAT-01..09, TEST-02) — full requirement text for this phase
- `.planning/ROADMAP.md` §Phase 4 — goal and success criteria (authoritative for verification)

### LLM Integration (MANDATORY — not open for revisiting)
- `.claude/skills/cerebras/SKILL.md` — the exact LiteLLM → OpenRouter → Cerebras (`gpt-oss-120b`) call pattern, including structured-outputs usage, that this phase's `/api/chat` implementation MUST follow

### Prior Phase Artifacts
- `.planning/phases/02-trading-portfolio/02-CONTEXT.md` D-01/D-03 — server-authoritative trade price, and why `execute_trade()` is float-typed/HTTP-agnostic specifically for this phase's direct calls
- `.planning/phases/03-visual-terminal-watchlist-control/03-CONTEXT.md` D-03 — the reserved `ChatPlaceholder` slot this phase replaces with live content (exact size/chrome already fixed, do not change without reason)
- `backend/app/db/schema.sql` — `chat_messages` table already exists (id, user_id, role, content, actions, created_at), lazily created since Phase 1, unused until now
- `backend/app/portfolio/service.py` `execute_trade()` — the HTTP-agnostic function this phase's chat handler calls directly for LLM-initiated trades (bypassing `TradeRequest`'s route-level integer constraint, per D-09 above the assistant still only ever passes whole numbers)
- `backend/app/watchlist/service.py` `add_ticker()` / `remove_ticker()` — the HTTP-agnostic functions this phase's chat handler calls directly for LLM-initiated watchlist changes
- `.planning/quick/260817-mlm-fix-apply-sell-s-exact-float-0-close-pos/260817-mlm-SUMMARY.md` — a just-shipped epsilon-threshold fix in `_apply_sell` anticipating fractional trades; not directly exercised this phase per D-09, but the fix is what makes leaving `execute_trade()` float-typed safe

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/components/ChatPlaceholder.tsx` — the component this phase replaces with a real chat panel; already sized/styled correctly (`h-64`/`min-h-64`, same chrome as Heatmap/PnlChart) per Phase 3 D-03
- `backend/app/portfolio/service.py` `execute_trade()`, `backend/app/watchlist/service.py` `add_ticker()`/`remove_ticker()` — HTTP-agnostic service functions, call directly from the chat handler rather than making internal HTTP requests
- `backend/app/db/database.py` — lazy-init/connection pattern (`contextlib.closing()`, `?`-placeholder SQL) to follow for `chat_messages` reads/writes
- `frontend/lib/trade.ts`, `frontend/lib/watchlistForm.ts` — result-union validation/error-mapping patterns (`{ ok: true|false }`) to mirror for chat message submission and error display
- `frontend/components/TradeBar.tsx`, `WatchlistAddForm.tsx` — non-optimistic submit/error UX precedent (disable while in-flight, inline error on failure) the chat input should match

### Established Patterns
- Backend: router-factory pattern (`create_stream_router`, `create_portfolio_router`, `create_watchlist_router`) — a `create_chat_router(cache)` should follow the same shape, registered in `backend/app/main.py` before the static catch-all mount
- Backend: frozen dataclasses for domain models, `?`-placeholder SQL exclusively, pydantic models for request/response validation
- Frontend: hand-built `<div>`-based components over UI-library primitives beyond shadcn `button`/`skeleton`/`input`; `frontend/lib/*.ts` pure state/derivation modules paired 1:1 with the component that renders them

### Integration Points
- `frontend/app/page.tsx` — swap `<ChatPlaceholder />` for the real chat panel component; page already owns `portfolioHistory`/`selectedTicker`/watchlist state this phase's assistant will need to reference or trigger refetches of after auto-executed actions
- `backend/app/main.py` — new `create_chat_router(cache)` registration, same ordering constraint as existing routers
- `PriceCache` — the chat handler's portfolio-analysis context (positions valued at current prices) reads from here, same single-source-of-truth constraint every prior phase established

</code_context>

<specifics>
## Specific Ideas

No specific chat UI mockups or exact copy given beyond the decisions above — bubble styling, action-card exact appearance, and typing-dots animation are open to the planner/UI-phase to design within the dark-terminal theme and Phase 1-3's established component conventions.

</specifics>

<deferred>
## Deferred Ideas

- Fractional/dollar-amount trades via chat ("buy $500 of AAPL") — explicitly deferred past this phase (D-09); schema and `execute_trade()` stay ready for it
- Proactive/unprompted trade suggestions — explicitly out of scope this phase (D-07); the assistant only acts when asked or agreed to in-turn

None — discussion stayed within phase scope beyond the above.

</deferred>

---

*Phase: 4-AI Copilot*
*Context gathered: 2026-08-17*
