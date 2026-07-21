# Review of PLAN.md

## Findings (ordered by severity)

### 1. High: LLM auto-execution safety controls are underspecified
Reference: PLAN.md lines 323-338

The plan allows automatic trade execution from model output with no confirmation. It mentions validation for cash/shares, but it does not define guardrails for:
- ticker allowlist and normalization rules
- max notional per trade
- max number of trades per chat response
- rejection behavior for ambiguous or partially valid actions
- audit fields to capture why a model action was accepted/rejected

Why this matters:
Without strict execution policy, prompt mistakes or model drift can create unstable behavior and hard-to-debug outcomes, even in a simulator.

Recommendation:
Define a deterministic "execution policy" section in the plan with hard limits and explicit rejection rules.

### 2. High: Trade consistency and race handling are not specified
Reference: PLAN.md lines 256-261, 292-299

Manual trade endpoint and chat-triggered trades can both update cash/positions. The plan does not specify transaction boundaries or concurrency policy.

Why this matters:
Two near-simultaneous requests can cause stale reads and inconsistent balances unless each trade is applied atomically.

Recommendation:
Require one database transaction per trade with read-modify-write in that transaction, plus a clear conflict strategy (retry or fail fast).

### 3. Medium: API contract is missing concrete response schemas
Reference: PLAN.md lines 249-278

Endpoint list is good, but response and error payloads are not defined in detail.

Why this matters:
Frontend/backend parallel work will drift without strict contracts.

Recommendation:
Add request/response examples for every endpoint, including validation errors and chat action results.

### 4. Medium: static export routing behavior is unclear
Reference: PLAN.md lines 65, 392

The plan uses Next.js static export served by FastAPI, but does not state route handling for deep links.

Why this matters:
Direct navigation to nested routes can 404 unless FastAPI serves the SPA fallback correctly.

Recommendation:
Add an explicit routing rule for serving index.html fallback for non-API paths.

### 5. Medium: environment variable requirements conflict with mock mode
Reference: PLAN.md lines 124-133, 342-345

OPENROUTER_API_KEY is marked required, but mock mode implies local/test runs without an API key.

Why this matters:
This causes confusion for first-time setup and CI.

Recommendation:
Clarify requirement as:
- required only when LLM_MOCK is false
- optional when LLM_MOCK is true

### 6. Medium: SSE payload/cadence details need operational limits
Reference: PLAN.md lines 176-180

The plan states frequent push updates but does not define heartbeat, no-change behavior, or payload versioning.

Why this matters:
Clients can mis-handle silent disconnects or overly noisy streams.

Recommendation:
Specify:
- heartbeat event interval
- whether unchanged prices are omitted
- event schema version field
- reconnect/backoff expectations

### 7. Medium: database lazy-init race is not addressed
Reference: PLAN.md lines 186-193

Lazy initialization is convenient, but startup behavior with multiple workers/processes is unspecified.

Why this matters:
Concurrent initialization can race on table creation and seed inserts.

Recommendation:
Add initialization lock strategy and idempotent seed guarantees.

### 8. Low: test strategy misses resilience/failure-path coverage
Reference: PLAN.md lines 426-456

Current test list covers happy paths well, but key failure modes are not explicit.

Recommendation:
Add tests for:
- malformed or partial LLM structured output
- OpenRouter timeout and fallback behavior
- SSE disconnect/reconnect with stale cache
- SQLite "database is locked" transient handling

## Open questions

1. Should watchlist and chat actions be processed synchronously in POST /api/chat, or queued and applied asynchronously with status polling?
2. Is fractional share precision bounded (for example 4 decimal places), and where is rounding defined?
3. Should the app preserve a full intraday price history in SQLite, or only portfolio snapshots and in-memory tick traces?

## Suggested PLAN.md additions (short list)

1. Add an "Execution Policy" subsection under LLM Integration.
2. Add concrete JSON schemas/examples for all API endpoints.
3. Add "Transactional guarantees" subsection under Database.
4. Add "SSE protocol details" subsection under Market Data.
5. Clarify environment variable requirements for mock vs live mode.

## Overall assessment

The plan is strong on product vision, UX clarity, and pragmatic architecture choices. The main gap is implementation-level contracts for safety, consistency, and operability. If the above constraints are added, this is ready for parallel agent implementation with lower integration risk.
