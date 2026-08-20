---
phase: 4
slug: ai-copilot
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-17
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8.3.0 (9.1.1 installed) + pytest-asyncio (`asyncio_mode = "auto"`), backend; Vitest ^4.1.10, frontend |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]`; `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/chat -x` — **must use `--extra dev`**; plain `uv run pytest` silently falls through to a system pytest lacking `pytest-asyncio` (known project gotcha) / `cd frontend && npm test -- lib/chat` |
| **Full suite command** | `cd backend && uv run --extra dev pytest` / `cd frontend && npm test` |
| **Estimated runtime** | ~2s (backend), ~1s (frontend) |

---

## Sampling Rate

- **After every task commit:** targeted `tests/chat/` file or `lib/chat` file for the module just touched
- **After every plan wave:** `cd backend && uv run --extra dev pytest` and `cd frontend && npm test` (full suites)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

*Reconciled 2026-08-20 against the actual executed plans and live-run test suite (State A audit — this table was seeded pre-execution with `TBD` task IDs and, in three rows, a since-corrected test target; all commands below were re-run and confirmed green).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01/04-02 | 04-01, 04-02 | 1, 2 | CHAT-01 | — | `POST /api/chat` returns `{message, actions}` shaped JSON | integration | `uv run --extra dev pytest tests/chat/test_routes.py -x` | ✅ | ✅ green |
| 04-03 | 04-03 | 2 | CHAT-02 | — | Portfolio context (positions, cash, concentration, P&L) reaches the LLM prompt | unit | `uv run --extra dev pytest tests/chat/test_prompt.py -x` (corrected target — draft named a nonexistent `test_service.py::test_build_portfolio_context`; the actual function `build_portfolio_context` lives in `app/chat/prompt.py` and is tested in `tests/chat/test_prompt.py`) | ✅ | ✅ green |
| 04-03/04-04 | 04-03, 04-04 | 2, 3 | CHAT-03 | V5 Input Validation | A trade proposed + agreed executes via `execute_trade()`, no confirmation; LLM output revalidated before write | unit (mocked `call_llm`) | `uv run --extra dev pytest tests/chat/test_service.py -k trade -x` | ✅ | ✅ green |
| 04-03/04-04 | 04-03, 04-04 | 2, 3 | CHAT-04 | V5 Input Validation | Watchlist add/remove executes via `add_ticker`/`remove_ticker`; LLM ticker revalidated before write | unit (mocked `call_llm`) | `uv run --extra dev pytest tests/chat/test_service.py -k watchlist -x` | ✅ | ✅ green |
| 04-03/04-04 | 04-03, 04-04 | 2, 3 | CHAT-05 | — | Insufficient-cash/oversell trade surfaces as plain-language explanation, portfolio unchanged | unit | `uv run --extra dev pytest tests/chat/test_service.py::TestExecuteActionsPartialFailure -x` (corrected target — draft's `-k rejected` filter matches 0 tests; the actual coverage is `TestExecuteActionsPartialFailure` plus `TestRejectionSentence`) | ✅ | ✅ green |
| 04-01/04-02 | 04-01, 04-02 | 1, 2 | CHAT-06 | — | History persists and is readable after reload (fresh `GET /api/chat/history`) | integration | `uv run --extra dev pytest tests/chat/test_routes.py -k history -x` | ✅ | ✅ green |
| 04-02 | 04-02 | 2 | CHAT-07 | — | Loading indicator shown while assistant thinks | — | none — no `.test.tsx` files exist anywhere in the repo (established convention: no component-rendering tests); `npm test -- ChatPanel` in the draft never matched anything real | ❌ (by convention) | manual-only |
| 04-01 | 04-01 | 1 | CHAT-08 | — | LLM call shape matches `.claude/skills/cerebras/SKILL.md` exactly (model, `extra_body`, `response_format`) | unit (assert call args on monkeypatched `litellm.completion`) | `uv run --extra dev pytest tests/chat/test_llm.py::TestCallLlmLive::test_live_call_uses_mandated_call_shape -x` | ✅ | ✅ green |
| 04-01/04-03 | 04-01, 04-03 | 1, 2 | CHAT-09 | V6 Cryptography (secret handling) | `LLM_MOCK=true` → deterministic response, zero network calls, no key echoed | unit | `uv run --extra dev pytest tests/chat/test_llm.py -k mock -x` | ✅ | ✅ green |
| 04-01/04-03 | 04-01, 04-03 | 1, 2 | TEST-02 | — | `parse_response()` handles valid and malformed JSON without crashing | unit | `uv run --extra dev pytest tests/chat/test_llm.py::TestParseResponse -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All Wave 0 files were created during execution and are confirmed present and green, with one exception noted below:

- [x] `backend/tests/chat/__init__.py`, `test_llm.py`, `test_service.py`, `test_routes.py`, `test_prompt.py` — new test package (executor split prompt-assembly coverage into its own `test_prompt.py` rather than folding it into `test_service.py` — a reasonable deviation)
- [x] `frontend/lib/chat.test.ts` — mirrors existing `lib/trade.test.ts`/`lib/watchlistForm.test.ts` shape
- [ ] `frontend/components/*.test.tsx` for the new chat components — **not created**. Consistent with the project's established convention (no component-rendering tests exist anywhere in the repo since Phase 1), this was never built; CHAT-07's loading indicator is covered by human verification instead (see Manual-Only below)
- Framework install: none — pytest-asyncio and Vitest already fully configured

---

## Manual-Only Verifications

All items below went through blocking human-verify checkpoints during execution and were approved with recorded evidence (`04-VERIFICATION.md`) — Phase 4 has no separate `04-UAT.md` file since sign-off happened inline per `04-04-SUMMARY.md`.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Typing-dots loading animation | CHAT-07 (D-03) | Requires watching the animation render in a browser; no `.test.tsx` files exist anywhere in the repo (established convention) | Send a chat message, confirm animated dots appear in place of the assistant's next bubble while waiting |
| Action-card visual rendering | D-04 | Visual confirmation of bordered action card styling | Trigger a trade or watchlist change via chat, confirm a distinct bordered card renders beneath the assistant's message |
| Chat bubble left/right alignment | D-01 | Visual layout confirmation | Send messages, confirm user bubbles align right and assistant bubbles align left |
| Auto-scroll on load and on new message | D-11 | Requires observing scroll position in a browser | Reload with existing history, confirm transcript is scrolled to newest message; send a new message, confirm it scrolls again |

---

## Validation Sign-Off

- [x] All tasks have automated verify or are correctly routed to Manual-Only
- [x] Sampling continuity: no gaps in automated coverage for testable requirements
- [x] Wave 0 covers all MISSING references (component-rendering tests deliberately not built, per established convention — routed to Manual-Only instead)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-20 (retroactive reconciliation; underlying requirements already independently confirmed in `04-VERIFICATION.md`)

## Validation Audit 2026-08-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 functional gaps. 10 rows had `TBD` task IDs; 3 rows (CHAT-02, CHAT-05, CHAT-07) named a test target that does not exist or matches nothing — reconciled against the actual test files. `04-01-SUMMARY.md`'s missing `requirements-completed` frontmatter (a separate, already-flagged documentation gap) was also fixed in this pass. |
| Resolved | 13 (Task ID / Plan / Wave columns filled for 10 rows; CHAT-02/CHAT-05 pointed at their real test targets; CHAT-07 reclassified from a fabricated `npm test -- ChatPanel` claim to accurately-described manual-only) |
| Escalated | 0 |
