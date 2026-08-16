---
phase: 01
slug: live-streaming-terminal
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-16
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser → FastAPI | Untrusted HTTP request paths and query strings cross into the app | HTTP requests |
| filesystem → StaticFiles | Request paths resolve to files on disk under the export directory | Static asset bytes |
| app → SQLite file | The user's persisted database — the only durable state in the system | Portfolio/watchlist state |
| npm registry → build | Third-party package code is executed at build time and shipped in the bundle | Build-time and shipped JS |
| SSE payload → DOM | Server-supplied ticker strings and numbers are rendered into the page | Ticker/price/direction values |
| SSE payload → animation state | Server-supplied `direction` and numeric values drive client-side render state | `direction` field |
| EventSource lifecycle → UI trust signal | Browser-level connection events determine what the user is told about data freshness | Connection status |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering | `app.mount("/", StaticFiles(...))` (`backend/app/main.py:81`) | medium | mitigate | Mounted directory is fixed from `FINALLY_STATIC_DIR` env var, never built from request input; mount registered after `/api/*` routes and the SSE router so those match first; Starlette StaticFiles normalizes/rejects traversal. Grep-confirmed live. | closed |
| T-01-04 | Tampering | SQL in `backend/app/db/database.py` | medium | mitigate | All statements use `?` placeholders (grep-confirmed: `INSERT OR IGNORE INTO users_profile (...) VALUES (?, ?, ?)` at line 83, `watchlist` at line 91); no f-string/`%`-formatted SQL anywhere in the module. | closed |
| T-01-05 | Tampering | `initialize()` in `backend/app/db/database.py` | high | mitigate | Schema is all `CREATE TABLE IF NOT EXISTS` (grep-confirmed, `schema.sql`); seeds are `INSERT OR IGNORE`; no `DROP`/`DELETE`/`TRUNCATE` anywhere in `backend/app/db/`. `test_second_init_preserves_mutated_cash_balance` in `backend/tests/test_db.py` asserts a mutated `cash_balance` survives a second `initialize()`. | closed |
| T-01-06 | Information disclosure | FastAPI error responses | low | accept | Uvicorn runs without `--reload`/debug mode; tracebacks stay server-side. App binds loopback only, holds no secrets in Phase 1. Revisit at Phase 5 when the container is published. | closed (accepted) |
| T-01-07 | Denial of service | `GET /api/stream/prices` | low | accept | Single-user loopback binding, no network exposure, no auth surface in Phase 1. Reconsider if Phase 5 exposes the container beyond localhost. | closed (accepted) |
| T-01-08 | Tampering | `WatchlistRow`/`PriceCell` rendering stream-supplied ticker and price values | low | mitigate | Values render as JSX text children (React-escaped); grep-confirmed zero uses of `dangerouslySetInnerHTML` in `frontend/components`, `frontend/app`, `frontend/lib`. Numeric fields pass through `formatPrice`/`formatPercent`. | closed |
| T-01-09 | Information disclosure | Static export bundle | low | accept | Frontend holds no secrets in Phase 1; calls only same-origin relative paths. Re-evaluate at Phase 4 when the chat panel arrives. | closed (accepted) |
| T-01-SC | Tampering | npm installs for `frontend/` scaffold (incl. vitest, jsdom, shadcn) | high | mitigate | Blocking human package-legitimacy checkpoint verified each package on npmjs.com before install (documented in STATE.md history). `vitest`/`jsdom` grep-confirmed present in `frontend/package.json` devDependencies as the only packages added beyond the original scaffold. | closed |
| T-01-10 | Tampering | `direction` field consumed by `PriceCell` via `directionGlyph` (`frontend/lib/flash.ts:39-43`) | low | mitigate | `directionGlyph` maps only `"up"`/`"down"` to glyphs and returns `""` for any other value — grep/read-confirmed; unexpected payload values render no glyph rather than arbitrary text. | closed |
| T-01-11 | Denial of service | Flash animation restart on every tick | low | accept | Ten rows at 2 Hz is well inside compositor budget; animation targets only `background-color`. Revisit if Phase 3 sparklines change per-row render cost. | closed (accepted) |
| T-01-12 | Spoofing | Connection indicator reporting health (`frontend/lib/usePriceStream.ts`, `frontend/lib/connection.ts`) | medium | mitigate | Status derives from `reduceConnection` fed by real `open`/`message`/`error` events plus a periodic staleness tick (`setInterval` at `usePriceStream.ts:51`), not from EventSource `readyState` alone — grep/read-confirmed. A wedged-but-open socket downgrades to Reconnecting. | closed |
| T-01-13 | Denial of service | EventSource reconnect behavior | low | accept | Reconnection delegated entirely to the browser's native backoff; no hand-rolled retry loop added. | closed (accepted) |
| T-01-14 | Information disclosure | Error copy shown to the user (`frontend/components/ConnectionIndicator.tsx`) | low | mitigate | Disconnected description is a fixed `DISCONNECTED_DESCRIPTION` constant rendered via `aria-describedby` — grep/read-confirmed; no exception text, endpoint, or stack detail surfaced. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01-01 | T-01-06 | Single-user loopback app, no secrets in Phase 1; revisit at Phase 5 container publish | Phase 1 threat model (PLAN.md) | 2026-08-11 |
| AR-01-02 | T-01-07 | Single-user loopback app, no auth surface in Phase 1; revisit at Phase 5 | Phase 1 threat model (PLAN.md) | 2026-08-11 |
| AR-01-03 | T-01-09 | Frontend holds no secrets in Phase 1; revisit at Phase 4 chat panel | Phase 1 threat model (PLAN.md) | 2026-08-12 |
| AR-01-04 | T-01-11 | Animation cost well within compositor budget at current scale; revisit at Phase 3 sparklines | Phase 1 threat model (PLAN.md) | 2026-08-13 |
| AR-01-05 | T-01-13 | Reconnection fully delegated to browser-native EventSource backoff, no custom retry surface | Phase 1 threat model (PLAN.md) | 2026-08-14 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-16 | 14 | 14 | 0 | Orchestrator (L1 grep-level verification, threats_open: 0, register authored at plan time, asvs_level: 1 — short-circuit per secure-phase workflow) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-16
