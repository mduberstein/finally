# Review of `planning/PLAN.md`

## Overall assessment

The plan communicates the product vision, major components, and intended demo experience clearly. The deliberately constrained scope—single user, simulated money, market orders, SSE, SQLite, and one deployable container—is appropriate for a capstone. The directory ownership and high-level division between frontend and backend are also clear enough for parallel work.

The main risk is that several important behaviors are described only narratively. Independent agents could make different reasonable choices and still believe they followed the plan. Before implementation, the plan should define canonical API/event contracts, data invariants, transaction semantics, and startup behavior.

## Highest-priority issues

### 1. Define complete API and SSE contracts

The endpoint list gives descriptions but not request/response schemas, status codes, or error bodies. Add an explicit contract for every endpoint, including:

- Exact JSON field names, types, nullability, and representative examples.
- A common error shape and the intended status codes for validation failure, missing ticker, unavailable price, insufficient cash/shares, duplicate watchlist entry, and upstream LLM/data-provider failure.
- Whether monetary and quantity values cross the API as JSON numbers or decimal strings.
- The precise SSE wire format: event name (if any), `id`, `retry`, whether each event contains one quote or a batch, timestamp format/timezone, heartbeat behavior, and cadence.
- Initial connection behavior: whether the server immediately emits a full snapshot before incremental updates.
- Contracts for loading existing chat history. The current API exposes only `POST /api/chat`, although the UI requires scrolling conversation history and the database persists it across restarts. Either add a read endpoint or explicitly state that history is session-only in the UI.

Without these details, frontend, backend, and E2E work cannot share a reliable contract.

### 2. Resolve which tickers must have live prices

The plan alternates among “all tickers known to the system,” “the user's watchlist,” and the union of watched tickers. These are not equivalent:

- A user may remove a ticker while still holding a position.
- A manual or LLM trade may name a ticker not currently watched.
- Portfolio valuation and snapshots still require current prices for held positions.

Define the subscribed universe as, at minimum, the union of watchlist tickers and position tickers, plus any ticker being validated for a pending trade. Also define how an unknown ticker is validated and how the first price is obtained before an order can fill. State whether executing a trade automatically adds its ticker to the watchlist.

### 3. Specify atomic trade and persistence semantics

Trade execution changes cash, positions, the append-only trade log, and a portfolio snapshot. These operations should occur in one database transaction. The plan should require:

- Atomic validation and mutation, so simultaneous manual/chat requests cannot overspend cash or oversell shares.
- Validation that quantity and price are finite and strictly positive; rejection of NaN, infinity, zero, and negative quantities.
- Ticker normalization and validation rules.
- The weighted-average-cost formula for buys, behavior for partial sells, and deletion (or retention) of a zero-quantity position.
- Numeric precision and rounding rules. SQLite `REAL` is convenient but can introduce visible cash/quantity drift; state whether calculations use `Decimal` and how values are stored/rounded.
- Database constraints/checks and foreign-key policy, rather than relying only on application validation.

### 4. Clarify LLM action execution and failure behavior

The sequence says the LLM creates a message, the backend then executes actions, and validation errors are included “so the LLM can inform the user.” The LLM cannot describe a failure discovered after its response unless there is a second model call or the backend rewrites/appends to the message.

Choose and document one behavior. A simple option is to return the original assistant message plus a backend-authored `action_results` array containing per-action success/failure details. Also define:

- Whether multiple actions are all-or-nothing or independently executed.
- Execution order when actions depend on one another.
- Whether later actions continue after one fails.
- The exact persisted form of requested actions versus actual results.
- Strict structured-output behavior: required arrays defaulting to empty is less ambiguous than optional fields.
- Timeout, malformed output, provider error, and retry behavior, including whether the user message is still saved.
- Whether duplicate client retries can execute a trade twice; an idempotency key or request ID should be considered for trade-capable requests.

### 5. Reconcile startup, environment, and Docker statements

Several statements conflict or need one authoritative interpretation:

- Database initialization is described as occurring “on startup (or first request)” and elsewhere as lazy initialization on first request. Pick one; startup initialization is easier to health-check and reason about.
- The Docker command uses the named volume `finally-data:/app/db`, but the text then says the project-root `db/` directory maps to `/app/db`. A named volume and a host bind mount are different. Specify which is canonical and align the directory-structure explanation and scripts.
- `OPENROUTER_API_KEY` is called required, while the product promises an immediately ready chat panel and supports development/testing without a key. Define startup and chat behavior when the key is absent and `LLM_MOCK=false`.
- “A browser opens” is not behavior a container can provide by itself. Make clear that this is a start-script convenience, while the raw Docker command only starts the server.
- For reproducibility, specify lockfile-based install commands (`npm ci` rather than `npm install`, and a frozen/locked `uv` sync) and name the expected frontend package manager/lockfile.

## Important product/data clarifications

### Market-data meaning

The frontend requires “daily change %,” but the shared cache only guarantees latest and previous streamed prices. Previous tick price is not previous close. Add `previous_close` (or explicitly rename the UI metric to change since connection) and define simulator behavior for it. Likewise, say whether the main chart is built only from samples since page load or requires historical candles; no historical-data endpoint currently exists.

Define stale-price behavior for Massive outages/rate limits: timestamp freshness threshold, UI indication, reconnect/provider backoff, and whether trading is blocked on stale quotes. The stated free-tier interval should also be configurable rather than embedding assumptions about a provider plan that may change.

### Portfolio and P&L definitions

Define formulas for total portfolio value, position weight, unrealized P&L, percent change, and the heatmap color scale. Clarify whether the “P&L chart” is actually total account value or profit/loss relative to the initial $10,000 (the schema stores only total value). Specify the initial snapshot, snapshot retention/order, and whether duplicate timestamps are possible.

### Watchlist and reset behavior

State maximum watchlist size, valid ticker format, case normalization, duplicate-add behavior, removal behavior for the selected ticker, and whether the ten defaults are reseeded only for a genuinely new database. A documented reset-data workflow would make demos and E2E runs much more predictable.

### Time and determinism

Require UTC ISO-8601 timestamps with an explicit `Z`/offset. For the simulator and E2E environment, define a fixed random seed, fixed initial prices, and any controllable clock/event settings so “deterministic” tests are actually reproducible.

## Testing gaps

The listed scenarios are a good start, but acceptance criteria should cover the core invariants and failure paths:

- Concurrent buys/sells cannot violate cash or holdings constraints.
- Invalid, unknown, zero, negative, NaN, and infinite trade inputs are rejected.
- Removing a held ticker does not stop portfolio valuation.
- Stale/unavailable market data blocks or handles fills according to the documented policy.
- Database restart preserves data and initialization is idempotent.
- LLM malformed output, timeout, partial action failure, and duplicate request retry cannot cause unintended duplicate trades.
- SSE tests verify initial snapshot, heartbeat, event schema/order, stale connection handling, and reconnect resynchronization—not just that a reconnect occurs.
- Snapshot calculations match the agreed formulas after buys, partial sells, full liquidation, and price changes.
- Production startup is tested without optional keys, with the expected degraded behavior.

Define measurable UI acceptance criteria where possible (supported viewport widths, reconnect timing, price-flash duration/tolerance, loading/empty/error states, and basic keyboard/accessibility behavior). “Visually stunning” and “functional on tablet” are useful direction but not testable completion criteria.

## Suggested plan additions

Before agents implement components, add four compact appendices to `PLAN.md`:

1. Canonical REST and SSE schemas with examples and errors.
2. Domain invariants and formulas for trades, positions, valuation, P&L, timestamps, precision, and ticker normalization.
3. Runtime lifecycle covering database initialization, background-task startup/shutdown, quote freshness, provider failure, and Docker volume/env behavior.
4. Acceptance criteria mapping each user-visible feature and important failure mode to a unit, integration, or E2E test.

With those additions, the document would serve not just as a strong product brief, but as a sufficiently precise shared contract for independently working coding agents.
