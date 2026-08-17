---
phase: 02
slug: trading-portfolio
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-16
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser → `POST /api/portfolio/trade` | Untrusted ticker, side, and quantity cross into the trade write path | Trade request body |
| trade path → SQLite | The only durable financial state in the system is mutated here | cash_balance, positions, trades rows |
| `PriceCache` → fill price | The value that determines how much money moves | Live price |
| concurrent requests → cash balance | Two callers can reach the same read-validate-write sequence | cash_balance, positions state |
| backend rejection detail → rendered DOM | Server-supplied error payload fields are interpolated into on-screen copy | ticker, owned, cash_balance figures |
| `/api/portfolio` payload → rendered DOM | Server-supplied ticker strings and numeric position fields are rendered into the page | position fields |
| SSE price payload → derived P&L | Stream-supplied prices drive the money figures a user makes decisions on | live price stream |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Tampering | SQL in `backend/app/portfolio/service.py` | high | mitigate | Every statement uses `?` placeholders — grep-confirmed zero f-string/`%`/`.format()` SQL in the module. | closed |
| T-02-02 | Tampering | Fill price for `POST /api/portfolio/trade` | high | mitigate | `TradeRequest` (`backend/app/portfolio/routes.py:16-23`) declares no fill-price field — grep/read-confirmed; price is read server-side from `PriceCache.get(ticker)` inside the transaction. | closed |
| T-02-03 | Tampering | Concurrent trade requests against `users_profile.cash_balance` | high | mitigate | `BEGIN IMMEDIATE` issued before the first read (`backend/app/portfolio/service.py:45-49`, grep/read-confirmed) takes the SQLite write lock up front; a dedicated concurrency test covers the race. | closed |
| T-02-04 | Tampering | `quantity` and `side` in the trade request body | medium | mitigate | Pydantic `Field(gt=0)` on an `int` and `Literal["buy","sell"]` (`routes.py:21-23`, grep-confirmed) reject zero/negative/fractional quantities and any other side before the database is opened. | closed |
| T-02-05 | Tampering | `ticker` string reaching `PriceCache` and SQL | medium | mitigate | Ticker uppercased (`service.py:39`, grep-confirmed `.strip().upper()`) and required to exist in `PriceCache` before any write; reaches SQL only as a bound `?` parameter. | closed |
| T-02-06 | Information disclosure | Trade rejection responses | low | accept | 400 detail carries only the user's own cash balance, owned share count, and ticker — data already visible in the header. Single-user loopback app. | closed (accepted) |
| T-02-SC | Tampering | Package-manager installs for this phase | low | mitigate | `02-RESEARCH.md` Package Legitimacy Audit records zero packages added across all 3 plans; `npx shadcn add input` writes a local component file, adds no dependency. No `[ASSUMED]`/`[SUS]`/`[SLOP]` entries. | closed |
| T-02-07 | Tampering | Sell branch in `backend/app/portfolio/service.py` | high | mitigate | Owned quantity read inside the same `BEGIN IMMEDIATE` transaction that performs the write; `quantity > owned` raises before any mutation. Proven by oversell and concurrency tests. | closed |
| T-02-08 | Tampering | Row removal when a position reaches zero | medium | mitigate | `DELETE FROM positions WHERE id = ?` (`service.py:187`, grep-confirmed) — scoped to `positions` table only, keyed by bound `?` parameter; zero `DELETE`/`DROP` statements touch the `trades` table anywhere in the package. | closed |
| T-02-09 | Tampering | Rejection detail interpolated by `tradeErrorMessage` | low | mitigate | Only `code`/`ticker`/`owned`/`cash_balance` fields are read into JSX text children (React-escaped); zero `dangerouslySetInnerHTML` in `frontend/lib/trade.ts`/`TradeBar.tsx` (grep-confirmed). Unrecognised code returns a fixed fallback sentence. | closed |
| T-02-10 | Denial of service | Rapid repeated trade submissions | low | accept | In-flight button disable plus the serializing `BEGIN IMMEDIATE` transaction bound practical throughput to one trade at a time. Single-user loopback app, no rate limit added. | closed (accepted) |
| T-02-11 | Tampering | Position fields rendered by `PositionRow` | low | mitigate | Every value renders as a JSX text child (React-escaped); numeric fields pass through `formatPrice`/`formatPercent`. Zero `dangerouslySetInnerHTML` in `PositionRow.tsx` (grep-confirmed). | closed |
| T-02-12 | Spoofing | A stale price presented as the live current price | medium | mitigate | `prices[ticker]?.price ?? position.price` (`frontend/lib/portfolio.ts:34,62`, grep-confirmed) — each row's price comes from the live SSE map when present, server snapshot otherwise; P&L is recomputed from whichever price is displayed so the two can never disagree. | closed |
| T-02-13 | Denial of service | Per-tick recomputation of position rows | low | accept | At most 10 positions recomputed at the existing 2 Hz stream cadence inside a `useMemo` on a pure function — well inside compositor budget. | closed (accepted) |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-06 | Rejection detail carries only the user's own already-visible cash/share/ticker data; single-user loopback app | Phase 2 threat model (02-01-PLAN.md) | 2026-08-16 |
| AR-02-02 | T-02-10 | Practical throughput already bound by UI disable + serializing transaction; single-user loopback, no auth surface to abuse | Phase 2 threat model (02-02-PLAN.md) | 2026-08-16 |
| AR-02-03 | T-02-13 | 10-row recomputation at 2 Hz is well inside compositor budget at current scale; revisit at Phase 3 heatmap/sparklines | Phase 2 threat model (02-03-PLAN.md) | 2026-08-16 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-16 | 13 | 13 | 0 | Orchestrator (L1 grep-level verification, threats_open: 0, register authored at plan time, asvs_level: 1 — short-circuit per secure-phase workflow) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-16
