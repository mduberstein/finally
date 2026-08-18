---
phase: 04-ai-copilot
plan: 02
subsystem: frontend-chat
tags: [react, nextjs, tailwind, vitest, chat-ui, typing-indicator]

requires:
  - phase: 04-ai-copilot plan 01
    provides: POST /api/chat, GET /api/chat/history, LLM_MOCK deterministic mode
provides:
  - frontend/lib/chat.ts (copy constants, send gating, transcript-assembly helpers)
  - frontend/components/ChatPanel.tsx (live AI Copilot panel, replacing ChatPlaceholder)
  - frontend/components/ChatMessage.tsx (user/assistant bubble)
  - frontend/components/ChatTypingIndicator.tsx (typing-dots loading signal)
affects: [04-ai-copilot plan 03 (action execution), 04-ai-copilot plan 04 (action cards)]

actuals:
  tokens: 5224
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - Pure-module-plus-component pairing (frontend/lib/chat.ts is the sole owner of every
      chat sentence and state transition; ChatPanel.tsx consumes it, holds no inline copy)
    - Time-injected pure functions (appendUserMessage/appendAssistantReply take a
      caller-supplied ISO timestamp, matching lib/flash.ts's nextFlashState convention —
      no Date.now() inside lib/chat.ts)
    - Optimistic-append-with-rollback (dropLastMessage undoes a failed send so the
      client transcript never diverges from what a reload would restore)

key-files:
  created:
    - frontend/lib/chat.ts
    - frontend/lib/chat.test.ts
    - frontend/components/ChatPanel.tsx
    - frontend/components/ChatMessage.tsx
    - frontend/components/ChatTypingIndicator.tsx
  modified:
    - frontend/app/globals.css
    - frontend/app/page.tsx
  deleted:
    - frontend/components/ChatPlaceholder.tsx

key-decisions:
  - "Accepted the mock-mode typing-dots timing as a testability artifact, not a bug — see Issues Encountered"
  - "createdAt is a required, caller-supplied parameter on appendUserMessage/appendAssistantReply (not optional), matching lib/flash.ts's nextFlashState(prev, direction, now) time-injected convention exactly"
  - "REQUIREMENTS.md's CHAT-07 checkbox was updated manually (gsd-tools runtime lib is unbuilt in this environment) rather than via `requirements mark-complete`"

requirements-completed: [CHAT-01, CHAT-06, CHAT-07]

coverage:
  - id: D1
    description: "Pure chat module (frontend/lib/chat.ts) owns every chat copy string and transcript state transition"
    requirement: "CHAT-01"
    verification:
      - kind: unit
        ref: "frontend/lib/chat.test.ts (13 tests: canSendChatMessage gating, appendUserMessage/appendAssistantReply immutability, dropLastMessage rollback, copy-constant text match)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Live ChatPanel: history restores on load, sending shows typing dots then a reply bubble, a failed send rolls back cleanly, 256px box scrolls instead of growing, color discipline (Accent Yellow on exactly two elements), reduced-motion static-dots fallback"
    requirement: "CHAT-01, CHAT-06, CHAT-07"
    verification:
      - kind: automated_ui
        ref: "Task 3 checkpoint: human browser verification against a live server (LLM_MOCK=true, then LLM_MOCK unset for real-latency confirmation) — 5 checks (color discipline, typing dots, reduced motion, layout at 1600px/800px, long-text wrap, failed-history-load empty state) all passed, approved by the human reviewer"
        status: pass
    human_judgment: true
    rationale: "Visual/timing/animation correctness (bubble alignment, stripe color, dot pulse, layout reflow) requires a human eye — cannot be fully proven by grep/unit tests alone, per this plan's own checkpoint:human-verify gate"

duration: "~50 min active work (wall-clock spanned longer — see Issues Encountered)"
completed: 2026-08-18
status: complete
---

# Phase 4 Plan 2: Live AI Copilot Chat Panel Summary

**Replaced the inert `ChatPlaceholder` with a working chat panel — bubble transcript restored from `GET /api/chat/history` on mount, `POST /api/chat` send with an animated typing-dots indicator and optimistic-bubble rollback on failure, all copy and state transitions centralized in a pure `frontend/lib/chat.ts` module.**

## Performance

- **Duration:** ~50 min of active execution (see Issues Encountered for a wall-clock note)
- **Completed:** 2026-08-18
- **Tasks:** 2 code tasks + 1 human-verify checkpoint (Task 3)
- **Files modified:** 8 (5 created, 2 modified, 1 deleted)

## Accomplishments

- `frontend/lib/chat.ts` — the single source of every chat sentence and transcript state transition (`canSendChatMessage`, `appendUserMessage`, `appendAssistantReply`, `dropLastMessage`), pure and time-injected, pinned by 13 Vitest cases
- `ChatPanel` fills the reserved AI Copilot slot: Skeleton while `GET /api/chat/history` is in flight, empty-state prompt on empty/failed history, scrolling bubble transcript with auto-scroll-to-newest, pinned input row disabled while submitting, inline `role="alert"` error with optimistic-bubble rollback on a failed send
- `ChatMessage` bubble (user right-aligned, assistant left-aligned with the first real use of Accent Yellow `#ecad0a` as a 2px left stripe) and `ChatTypingIndicator` (three CSS-keyframe dots occupying the next reply's position, with a `prefers-reduced-motion` static-dots fallback)
- CHAT-07 requirement (loading indicator while waiting for the LLM response) closed out — CHAT-01 and CHAT-06 already carried a partial checkmark from Plan 01's backend delivery; this plan completes their user-facing half

## Task Commits

Each task was committed atomically:

1. **Task 1: The pure chat module — copy constants, send gating, and transcript assembly** - `8504040` (feat, TDD: test written and confirmed failing before implementation)
2. **Task 2: The live AI Copilot panel — transcript, pinned input, typing dots, restored history** - `96ffe78` (feat)

Task 3 was a `checkpoint:human-verify gate="blocking"` — no code commit; verified live in-browser, approved by the human reviewer (see Issues Encountered for the mock-timing investigation that preceded approval).

**Plan metadata:** this SUMMARY.md + REQUIREMENTS.md commit (worktree mode — STATE.md/ROADMAP.md are the orchestrator's responsibility after merge).

## Files Created/Modified

- `frontend/lib/chat.ts` - Chat types (`ChatMessageRecord`, `ChatAction`, `ChatReply`), copy constants, `canSendChatMessage`/`appendUserMessage`/`appendAssistantReply`/`dropLastMessage`
- `frontend/lib/chat.test.ts` - 13 Vitest cases pinning gating, immutable append/rollback, and copy-constant text
- `frontend/components/ChatPanel.tsx` - History fetch, transcript render, send flow with optimistic append/rollback, typing-indicator wiring
- `frontend/components/ChatMessage.tsx` - One bubble; renders `content` as a React text node only, never `dangerouslySetInnerHTML` (T-04-09)
- `frontend/components/ChatTypingIndicator.tsx` - Three-dot CSS loading signal in the assistant bubble shell
- `frontend/app/globals.css` - `typing-dot` keyframes, `.animate-typing-dot` utility, extended `prefers-reduced-motion` block
- `frontend/app/page.tsx` - `<ChatPlaceholder />` → `<ChatPanel />`
- `frontend/components/ChatPlaceholder.tsx` - Deleted (dead component; slot is now filled)

## Decisions Made

- **`createdAt` is a required parameter, not optional**, on `appendUserMessage`/`appendAssistantReply` — matches `lib/flash.ts`'s `nextFlashState(prev, direction, now)` time-injected convention exactly, keeping `lib/chat.ts` fully deterministic (no `Date.now()`, no `new Date()`) per the plan's own acceptance-criteria grep.
- **Mock-mode typing-dot timing accepted as-is, no artificial delay added** — see Issues Encountered for the full root-cause investigation. `LLM_MOCK=true`'s design intent (PLAN.md §9) is fast/deterministic for automated tests; the real (`LLM_MOCK=false`) path already produces a visible multi-second delay, confirmed live.
- **REQUIREMENTS.md's CHAT-07 checkbox updated by hand** rather than via `gsd-tools query requirements.mark-complete` — the GSD runtime lib is unbuilt in this environment (`tsconfig.build.json` missing, confirmed both in this worktree and the main checkout, so not worktree-specific). Edit matched the file's existing formatting exactly (checkbox + traceability table row).

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes were needed; both tasks' acceptance criteria (grep checks, `npm test`, `npm run lint`, `npx next build --webpack`) passed without code changes beyond what the plan specified.

## Issues Encountered

**1. Stalled background build poller (infrastructure, not a code defect).** The first `npx next build --webpack` invocation was moved to background execution by the harness after a timeout, and a follow-up poller waiting on `.next/BUILD_ID` never fired — the build had silently died mid-`compile` stage (per `.next/diagnostics/build-diagnostics.json`), and the poller was waiting on a file that would never appear. The orchestrator caught this from the outside (no live `next-build` process, no `frontend/out/`, stale `.next/` mtime) and directed recovery: `rm -rf frontend/.next`, then re-run the build **in the foreground** to get a real exit code. The foreground re-run compiled cleanly in ~14s total and produced `frontend/out/`. This is the wall-clock gap between Task 1's commit (22:14 local) and Task 2's commit (07:27 local the next morning) — active work was concentrated at the start and end of that window, not spread across it.

**2. Task 3 checkpoint — typing-dots not visually perceptible under `LLM_MOCK=true`.** Human verification reported Test 1 (typing dots) failing: "the Mock response returns immediately... likely because LLM_MOCK=true." Investigated root cause per CLAUDE.md convention (prove before fixing, don't guess) rather than assuming either a real bug or dismissing the report:
   - **Code trace:** `ChatPanel.submitMessage` calls `setMessages`/`setSubmitting(true)` synchronously before the first `await`, so React batches them into one render with the typing indicator mounted — the state transition is provably correct, not racy, and `appendAssistantReply` always appends (never replaces) the optimistic user bubble.
   - **Measured evidence:** `POST /api/chat` under `LLM_MOCK=true` resolved in ~2.7–3.2ms across three live measurements against the running verification server — far below a single ~16ms browser paint frame, so the intermediate "dots visible" render is real but the browser almost never gets a chance to paint it before the final state replaces it.
   - **Corroboration:** restarted the verification server without `LLM_MOCK` (real `OPENROUTER_API_KEY` from repo-root `.env`, passed directly into the subprocess environment without ever being printed to any tool output) and measured a real round-trip of 4.25s with a genuine ("Hello.") Cerebras reply — more than three full 1.2s typing-dot animation cycles, clearly visible.
   - **Conclusion (documented, no code change):** this is a testability artifact of `LLM_MOCK=true`'s intentionally-instant design (PLAN.md §9: "Fast, free, reproducible E2E tests"), not a functional defect. CHAT-07 is satisfied — the indicator occupies the correct position for the full duration of any real request. Adding an artificial delay to the mock path was rejected: it would touch Plan 01's already-tested, out-of-scope backend code (`backend/app/chat/llm.py`) and work against the mock path's whole purpose of keeping Phase 5's Playwright suite fast.
   - The human independently ran their own server instance (real backend, scratch DB) and confirmed all 5 checkpoint checks pass, including the real-latency typing dots and the reduced-motion static-dots fallback. **Approved.**

## User Setup Required

None - no external service configuration required. (The real-latency verification used the `.env` `OPENROUTER_API_KEY` already confirmed working by Plan 01's tracer gate; no new secret or setup step was introduced by this plan.)

## Next Phase Readiness

- `ChatMessage` already accepts an optional `children` prop, ready for Plan 04's action cards to slot in beneath the assistant bubble without restructuring.
- `ChatAction` is deliberately permissive (all-optional record) so Plan 04 can narrow it into a discriminated union once it renders action cards.
- No blockers. Plan 03 (portfolio-context injection and action execution) and Plan 04 (action cards) can proceed against this panel unchanged.
- Verification server, scratch DB, and `backend/static` copy from this plan's checkpoint have all been cleaned up — nothing left running, no scratch artifacts remain in the worktree.

---

## Self-Check: PASSED

- `frontend/lib/chat.ts` — FOUND
- `frontend/lib/chat.test.ts` — FOUND
- `frontend/components/ChatPanel.tsx` — FOUND
- `frontend/components/ChatMessage.tsx` — FOUND
- `frontend/components/ChatTypingIndicator.tsx` — FOUND
- `frontend/components/ChatPlaceholder.tsx` — CONFIRMED REMOVED
- Commit `8504040` (feat: pure chat module) — FOUND in `git log`
- Commit `96ffe78` (feat: live AI Copilot panel) — FOUND in `git log`

---
*Phase: 04-ai-copilot*
*Completed: 2026-08-18*
