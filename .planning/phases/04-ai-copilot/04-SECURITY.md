---
phase: 04
slug: ai-copilot
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-18
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser → `POST /api/chat` | An untrusted free-text string crosses into a paid external API call for the first time in this project | User-authored chat message |
| backend → OpenRouter/Cerebras | A bearer credential and the user's own portfolio context leave the process | `OPENROUTER_API_KEY`, portfolio context |
| OpenRouter/Cerebras → `parse_response` | Untrusted model output crosses back in and is deserialized into a domain object | LLM-generated JSON |
| `chat_messages` table → every later chat turn | Persisted content is replayed into the next prompt | Prior chat history |
| backend JSON → React render tree | Model-generated text, which no human reviewed, crosses into the DOM | LLM reply text |
| `GET /api/chat/history` → transcript | Previously persisted, model-generated content is replayed into the DOM on every page load | Persisted chat history |
| model output → `execute_trade` | Model-proposed tickers, sides, and quantities cross into the money tables | Trade actions |
| model output → `add_ticker` / `remove_ticker` | Model-proposed symbols cross into the table the market feed polls | Watchlist actions |
| portfolio state → outbound prompt | The user's own positions and cash leave the process toward OpenRouter | Cash, positions, P&L, watchlist |
| persisted action payload → rendered card | Model-originated action data crosses into a claim about what happened to the user's money | Action execution results |
| chat reply → portfolio refetch | A model-driven turn triggers reads of the portfolio and watchlist endpoints | Refetch trigger |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Information disclosure | OpenRouter bearer credential in `backend/app/chat/llm.py` | high | mitigate | Credential never resolved/stored/logged/returned by the chat package; LiteLLM reads it from process env. Parse-failure logs emit only a truncated output excerpt. Verified: zero `getenv`/`api_key`/`Authorization`/`Bearer` hits in `backend/app/chat/*.py`. | closed |
| T-04-02 | Tampering | SQL reading/writing `chat_messages` in `backend/app/chat/service.py` | high | mitigate | All SELECT/INSERT bind via `?` placeholders, no interpolation. Verified in `service.py:37-41,245-261`. | closed |
| T-04-03 | Denial of service | Oversized chat body driving latency/API spend | medium | mitigate | `MAX_MESSAGE_LENGTH=4000` via pydantic `StringConstraints`, 422 before any model call. Verified `models.py:17`, `routes.py:21-24`. | closed |
| T-04-04 | Tampering | Untrusted model output deserialized by `parse_response` | high | mitigate | `ChatResponse.model_validate_json` in `try/except (ValidationError, ValueError)`; failure returns fallback + HTTP 200. Verified `llm.py:120-128`. | closed |
| T-04-05 | Information disclosure | Prompt injection extracting system prompt | low | accept | System prompt carries persona/tone/schema instructions only, no credential/path/config. See Accepted Risks Log. | closed |
| T-04-06 | Repudiation | Chat turns carry no attribution beyond timestamp | low | accept | Single hardcoded `user_id`, append-only log with `created_at`. See Accepted Risks Log. | closed |
| T-04-07 | Tampering | `load_dotenv` reading repo-root file into process env | low | mitigate | No `override=True`; env var/`--env-file` always wins. `.env` gitignored. Verified `main.py:24`. | closed |
| T-04-08 | Denial of service | Synchronous LiteLLM round-trip stalling event loop | medium | mitigate | `run_in_threadpool(handle_chat_message, ...)` in both chat routes. Verified `routes.py:41,45`. | closed |
| T-04-SC-01 | Tampering (supply chain) | `uv add litellm pydantic python-dotenv` (Plan 01) | high | mitigate | `litellm` cleared via blocking human legitimacy checkpoint (BerriAI ownership, multi-year release history); `pydantic`/`python-dotenv` OK. Verified `pyproject.toml:12`, `uv.lock:897-899`, `04-01-SUMMARY.md:42`, commit `3c30222`. | closed |
| T-04-09 | Tampering | Model-generated text rendered by `ChatMessage` | high | mitigate | Renders as React text child (auto-escaped); zero `dangerouslySetInnerHTML`/`innerHTML`/`eval` in any chat component. Verified `ChatMessage.tsx:29`. | closed |
| T-04-10 | Tampering | Model-generated text used as anything other than display text | medium | mitigate | No chat component derives URL/href/src/style/DOM id from message content. Verified — only constant literals found. | closed |
| T-04-11 | Information disclosure | Secrets reaching browser through chat panel | low | accept | Panel calls only same-origin `/api/chat`, `/api/chat/history`; no absolute-URL fetch or credential token in frontend source. See Accepted Risks Log. | closed |
| T-04-12 | Denial of service | Unbounded transcript growth in browser | low | mitigate | `HISTORY_LIMIT=100` server-side default; fixed 256px scrolling box client-side. Verified `service.py:23`, `ChatPanel.tsx:117,123`. | closed |
| T-04-13 | Denial of service | Oversized draft submitted from client | low | mitigate | `MAX_CHAT_MESSAGE_LENGTH=4000`, `canSendChatMessage` + `maxLength` gate; server (T-04-03) is the real boundary. Verified `lib/chat.ts:58,71-75`, `ChatPanel.tsx:164,170`. | closed |
| T-04-14 | Spoofing | Transcript bubble not reflecting persisted server state | medium | mitigate | Failed send rolls back optimistic bubble via `dropLastMessage`, restores draft. Verified `ChatPanel.tsx:88-93,101-104`. | closed |
| T-04-SC-02 | Tampering (supply chain) | Package-manager installs (Plan 02) | low | mitigate | No new npm dependency — `git diff` on `frontend/package.json` across the phase is empty for this plan. | closed |
| T-04-15 | Elevation of privilege | Model-proposed trades reaching positions/trades/users_profile/portfolio_snapshots | high | mitigate | Every action routed through `execute_trade`/`add_ticker`/`remove_ticker` — same functions the manual UI uses, all validation intact. Chat package issues no SQL against any table but `chat_messages`. Verified `service.py:15,17,111,142,166`. | closed |
| T-04-16 | Tampering | Model-supplied ticker strings | high | mitigate | `execute_trade` normalizes `strip().upper()`, refuses ticker absent from `PriceCache`; `normalize_ticker` enforces `^[A-Z]{1,10}$`. Verified `service.py:89,137`, `portfolio/service.py:51-54`, `watchlist/service.py:20,41,71`. | closed |
| T-04-17 | Tampering | Model-supplied trade quantities (fractional/negative) | medium | mitigate | `TradeAction.quantity: int` in strict schema, plus explicit positive-whole-number guard before `execute_trade`. Two independent layers. Verified `models.py:33`, `service.py:93-108`. | closed |
| T-04-18 | Tampering | Prompt injection steering assistant into unwanted action | medium | mitigate | Injected instruction can only produce an action the user could already perform via UI; every action passes same validation, persisted + rendered as a card. Verified `service.py:85-205,251-261`, `ChatPanel.tsx:129-140`. | closed |
| T-04-19 | Information disclosure | User's cash/positions/P&L sent to OpenRouter in every prompt | low | accept | This is the data the assistant exists to reason about — the user's own simulated data, OpenRouter is the PLAN.md-fixed provider, no credential/path/config in the context block. See Accepted Risks Log. | closed |
| T-04-20 | Denial of service | One failing action aborting a turn's remaining actions | medium | mitigate | Each action in its own `try`/`except`, loop always continues. Verified `service.py:110-134,141-163,165-178`. | closed |
| T-04-21 | Repudiation | Executed action leaving no record | medium | mitigate | Every executed/failed action persisted in assistant row's `actions` column; executed trades also land in append-only `trades` + `portfolio_snapshots` inside same transaction. Verified `service.py:251-261`, `portfolio/service.py:80,83`. | closed |
| T-04-SC-03 | Tampering (supply chain) | Package-manager installs (Plan 03) | low | mitigate | No `uv add` or `npm install` — both manifests unchanged since Plan 01. | closed |
| T-04-22 | Spoofing | Action card implying trade/watchlist change that never happened | high | mitigate | `actionCardText` returns null unless payload status is exactly the executed marker; `ChatActionCard` has no other render path. Verified `lib/chat.ts:12,134`, `ChatActionCard.tsx:17-18`, `ChatPanel.tsx:129-131`. | closed |
| T-04-23 | Tampering | Model-originated action fields rendered without type checks | medium | mitigate | Every field guarded with `typeof`/equality checks; unrecognised shape returns null. Verified `lib/chat.ts:132,138-142,148,150-151,157-158`. | closed |
| T-04-24 | Information disclosure | Post-action refetch reading portfolio/watchlist state | low | accept | Calls same same-origin endpoints the manual UI already calls, returns only local user's own data. See Accepted Risks Log. | closed |
| T-04-25 | Spoofing | Stale main-chart price for a ticker the assistant removed | medium | mitigate | Watchlist refetch reconciles selection via `clearSelectionIfAbsent`, clearing a selection whose ticker is gone. Verified `page.tsx:72-77,88`, `selection.ts:32-38`. | closed |
| T-04-26 | Denial of service | Redundant refetching on every chat turn | low | mitigate | `onActed` fires only when at least one action executed. Verified `ChatPanel.tsx:99-100`. | closed |
| T-04-SC-04 | Tampering (supply chain) | Package-manager installs (Plan 04) | low | mitigate | No new npm dependency — `lucide-react` (already a direct dependency) supplies `CheckCircle2`. `frontend/package.json` diff across the phase is empty. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-01 | T-04-05 | Prompt injection extracting the system prompt is low-value: the prompt carries persona/tone instructions only, and the portfolio figures it later includes (Plan 03) are already visible to the user via the header and positions table. Single-user, zero-auth, zero-real-money simulator with no privilege to escalate to. | gsd-security-auditor (verified in code) | 2026-08-18 |
| AR-04-02 | T-04-06 | Chat turns carry no attribution beyond a timestamp. Single hardcoded `user_id="default"`, no multi-user compliance surface. Consistent with `T-01-06`/`T-02-06`/`T-03-05` acceptances — revisit only if a future phase exposes the container beyond localhost. | gsd-security-auditor (verified in code) | 2026-08-18 |
| AR-04-03 | T-04-11 | The chat panel calls only same-origin `/api/chat` and `/api/chat/history` and stores nothing but message text; no credential is present in the bundle. Closes Phase 1's deferred `T-01-09` ("frontend holds no secrets — revisit at Phase 4 chat panel"). | gsd-security-auditor (verified in code) | 2026-08-18 |
| AR-04-04 | T-04-19 | The user's cash, positions, and P&L are sent to OpenRouter in every prompt — but this is exactly the data the assistant exists to reason about, it's the user's own simulated data, and OpenRouter is the LLM provider PLAN.md fixes for the project. No credential, file path, or configuration detail is in the context block. | gsd-security-auditor (verified in code) | 2026-08-18 |
| AR-04-05 | T-04-24 | The post-action refetch (portfolio + watchlist) calls the same same-origin endpoints the manual trade bar and watchlist form already call, returning only the local user's own data — identical to the accepted `T-02-06`/`T-03-10` dispositions. | gsd-security-auditor (verified in code) | 2026-08-18 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-18 | 30 | 30 | 0 | gsd-security-auditor (opus) |

**Observation (non-blocking, not a registered threat):** `call_llm` (`backend/app/chat/llm.py:49-56`) does not wrap `completion()` in a `try`/`except`, so a provider auth or transport failure propagates to FastAPI as a 500, and LiteLLM's own exception text lands in server logs. Outside every declared mitigation's scope (T-04-01 covers the chat package not resolving/storing/logging/returning the credential, which holds) and the log sink is a localhost single-user container. Worth registering as a threat in a later phase if the container is ever exposed beyond loopback — the same trigger condition already attached to the T-04-06 acceptance.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-18
