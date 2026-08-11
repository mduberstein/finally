# Review of PLAN.md

Reviewer: Claude (independent review)
Date: 2026-07-21
Scope: `planning/PLAN.md`, checked against the implemented backend in `backend/app/market/`, `planning/MARKET_DATA_SUMMARY.md`, `README.md`, and `.gitignore`.

## Verdict

The plan is strong as a product specification and the market data component built from it is clean, well-tested (73 tests confirmed), and matches its own design docs. The plan is **not yet strong enough as an agent contract**. Its weakest areas are the seams between components that different agents will build in parallel: the SSE payload shape, the meaning of "change %", the ticker lifecycle (watchlist vs. positions vs. data source), and price durability across restarts. Three defects below are latent bugs that will surface as soon as the portfolio component is wired to the existing price cache.

Findings are ordered by severity within each section. Section A is the highest-value part of this review because those items are already true in code, not hypothetical.

---

## A. PLAN.md and the implemented code have diverged

### A1. High — "Daily change %" is specified in the UI but is not computable from anything that exists

PLAN.md line 355 requires the watchlist to show "daily change %". Line 179 says each SSE event carries "ticker, price, previous price, timestamp, and change direction".

In `backend/app/market/cache.py:31-38`, `previous_price` is the price from the **immediately preceding tick** (~500 ms ago). `PriceUpdate.change_percent` (`models.py:24-28`) is therefore a tick-over-tick delta, typically a few thousandths of a percent — not a daily change. Nothing in the system records a session open price, a previous close, or a daily anchor:

- The simulator seeds from `SEED_PRICES` (`seed_prices.py:4-15`) and never retains that value as an "open".
- `MassiveDataSource._poll_once` (`massive_client.py:99-108`) reads only `snap.last_trade.price`, discarding the snapshot's day/prevDay aggregates that Polygon returns and that would give a real daily change.

Consequence: a frontend agent implementing line 355 literally will render a column that is always ~0.00%, and will have no way to fix it without a backend change. Two different agents will each reasonably believe the other owns it.

Recommendation: decide explicitly and write it into the plan. Either (a) rename the column to "tick change" and accept it, or (b) add an `open_price`/`prev_close` field to `PriceUpdate`, seeded at start for the simulator and read from the Massive snapshot's `prevDay.c`, and define `change_percent` against it. Option (b) is a small change and is what a trading terminal actually shows. Note that this also changes the flash semantics, which currently key off tick direction.

### A2. High — Removing a ticker from the watchlist destroys the price of any position you still hold

`SimulatorDataSource.remove_ticker` (`simulator.py:251-255`) and `MassiveDataSource.remove_ticker` (`massive_client.py:72-76`) both call `self._cache.remove(ticker)`. `PriceCache.get_price` then returns `None` for that ticker.

PLAN.md line 268 exposes `DELETE /api/watchlist/{ticker}` with no stated precondition, and line 259 requires `GET /api/portfolio` to return current value and unrealized P&L. If the user holds AAPL and removes it from the watchlist, portfolio valuation loses the price it needs. The plan never states the relationship between the watchlist, open positions, and the data source's tracked ticker set — it asserts the opposite at line 178 ("all tickers known to the system ... is equivalent to the user's watchlist").

Recommendation: state the invariant in the plan: **tracked tickers = watchlist ∪ tickers with a non-zero position**, and `DELETE /api/watchlist/{ticker}` must not call `source.remove_ticker()` while a position is open. Also specify who calls `add_ticker`/`remove_ticker` — the plan currently never says that the watchlist endpoints must drive the market data source at all, which is the single most important integration point between the built component and the unbuilt one.

### A3. High — Prices reset on restart while positions persist, producing phantom P&L

`GBMSimulator._add_ticker_internal` (`simulator.py:151`) always seeds from the `SEED_PRICES` constant. The cache is in-memory only. Meanwhile PLAN.md sections 7 and 11 guarantee that positions, `avg_cost`, and `portfolio_snapshots` survive container restarts via the volume.

So: buy NVDA at a simulated $860 after an hour of drift, restart the container, and NVDA is back at $800. The user's unrealized P&L jumps by -$60/share with no trade, and the P&L chart shows a discontinuity that looks like a bug because it is one.

Recommendation: add a "price durability" rule to the plan. Cheapest fix consistent with the existing design: persist the last price per ticker (a `last_prices` table or reuse of the snapshot mechanism) and have `SimulatorDataSource.start` prefer the persisted price over `SEED_PRICES`. Alternatively, state plainly that a restart resets the market and that the demo accepts it — but the plan must say which, because the portfolio agent cannot infer it.

### A4. Medium — The SSE payload in the plan does not match the SSE payload on the wire

PLAN.md line 179 describes a per-ticker event. `stream.py:81-83` emits a **single event containing a map of every tracked ticker**:

```
data: {"AAPL": {"ticker":"AAPL","price":190.5,"previous_price":190.48,"timestamp":...,"change":0.02,"change_percent":0.0105,"direction":"up"}, ...}
```

There is no `event:` name, and the payload carries `change` and `change_percent` which the plan does not mention. A frontend agent coding to the plan will write a parser that does not work.

Also divergent: line 178's "~500ms cadence" is simulator-only. `MassiveDataSource` polls every 15 s by default (`massive_client.py:32`), and `stream.py:76` only emits when `price_cache.version` changes, so with the Massive source the stream emits roughly every 15 s, and **not at all** when the market is closed or the API is failing.

Recommendation: paste the actual payload into the plan as the normative contract, and add the operational rules the prior review also asked for: heartbeat interval (needed so the connection dot at line 37 does not go yellow during a legitimate 15 s Massive gap or a weekend), whether unchanged tickers are re-sent, and a schema version field.

### A5. Medium — Re-sent unchanged tickers will cause spurious price flashes

Related to A4 but a distinct frontend bug. `stream.py` sends the **whole cache** whenever the version counter moves. Under the Massive source a poll may update 3 of 10 tickers; the other 7 are re-sent unchanged. PLAN.md line 368 instructs the frontend to "on receiving a new price, briefly apply a CSS class" — receiving, not changing. That flashes all ten tickers.

Recommendation: change line 368 to specify that the flash triggers on a **changed price value** compared to the client's last known value for that ticker, and that `direction` from the payload is advisory.

### A6. Medium — `create_stream_router` registers duplicate routes and can bind the wrong cache

`stream.py:17` defines `router` at module scope; `create_stream_router` decorates that shared object and returns it. Verified:

```
r1 = create_stream_router(cache); r2 = create_stream_router(cache)
same object: True
routes: ['/api/stream/prices', '/api/stream/prices']
```

Two calls register the path twice on one router. Worse, each call closes over a different `price_cache`, but FastAPI matches the first registered route — so a second call with a different cache is silently ignored. This will bite in tests and in any app-factory pattern (`create_app()` per test), which is the normal way to test FastAPI.

Recommendation (implementation fix, not a plan change): move `router = APIRouter(...)` inside the factory function. One-line change, no API impact.

### A7. Medium — Any string is a valid ticker under the simulator, and the two sources disagree

`simulator.py:151`: `SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))`. Adding `ZZZZZ` to the watchlist yields a real-looking price and a tradeable position. Under `MassiveDataSource` the same ticker simply never receives a price and renders blank forever. The plan's central claim — "Both the simulator and the Massive client implement the same abstract interface ... All downstream code is agnostic to the source" (line 148) — does not hold for unknown symbols.

This matters more than it looks because PLAN.md line 336 tells the LLM to "Manage the watchlist proactively", so a hallucinated symbol reaches `add_ticker` with no human in the loop.

Recommendation: add a ticker validation rule to the plan — normalization (upper, strip), a format regex, and either a symbol allowlist or a documented "unknown symbols are accepted and simulated" stance. Define the API error shape for a rejected ticker. Also define what `POST /api/portfolio/trade` does when the cache has no price for the requested ticker (must be a clean 4xx, not a crash or a `None` price).

### A8. Low — `.env` is not actually read by the backend

PLAN.md line 140 states "The backend reads `.env` from the project root". It does not. `factory.py:24` reads `os.environ` directly, and `python-dotenv` appears in `uv.lock` only as a transitive extra of `uvicorn[standard]` — it is not a declared dependency in `backend/pyproject.toml` and nothing in `app/` imports it.

In Docker this is harmless because `--env-file` populates the process environment. For local `uv run` development it means `MASSIVE_API_KEY` and `OPENROUTER_API_KEY` are simply absent unless manually exported.

Recommendation: reword line 140 to "environment variables are read from the process environment; Docker supplies them via `--env-file`", and if local dev convenience is wanted, add `python-dotenv` as an explicit backend dependency with a documented load point.

### A9. Low — `MARKET_DATA_SUMMARY.md` is accurate

For completeness: I verified the summary's claims. 73 test functions exist, the module list matches, and the seven listed review fixes are present in the code (hatch wheel packages, top-level `massive` import, `AsyncGenerator` annotation, public `get_tickers`, consolidated `CROSS_GROUP_CORR`). No divergence found here.

---

## B. Contract gaps that will break parallel agent work

### B1. High — No ASGI application entrypoint is named anywhere

PLAN.md line 389 says "CMD: uvicorn serving FastAPI app". No module path is given. There is currently **no FastAPI app object in the repo at all** — `backend/app/` contains only the market package; there is no `main.py`, no `create_app()`, no `app = FastAPI()`.

Three agents need this string: the backend agent creates it, the Dockerfile agent invokes it, the E2E agent starts it. Nothing in the plan lets them agree.

Recommendation: fix it in the plan now — e.g. `backend/app/main.py` exposing `app`, started as `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Also specify that startup must construct the `PriceCache`, call `create_market_data_source(cache)`, and `await source.start(watchlist_tickers)` in a lifespan handler, and shut it down on exit. The existing `MARKET_DATA_SUMMARY.md` "Usage for Downstream Code" snippet should be lifted into PLAN.md, because that is the contract.

### B2. High — No historical price data exists, but the plan asks for a chart of it

PLAN.md line 356 requires a "Main chart area — larger chart for the currently selected ticker, with at minimum price over time". Section 8 defines no price-history endpoint, and no table stores ticks. The only stated source is SSE accumulation since page load (line 25, for sparklines).

So the main chart is empty on load and fills in over minutes. That may be an acceptable deliberate choice, but it is not stated, and a frontend agent will look for `/api/prices/history`, not find it, and either invent one or block.

Recommendation: state the decision explicitly in section 10. If accepted as-is, say "the main chart shares the SSE-accumulated buffer and starts empty". If not, add `GET /api/prices/{ticker}/history` to section 8 and a `price_history` table or a bounded in-memory ring buffer to section 6. I would recommend a small server-side ring buffer (e.g. last 600 ticks per ticker) — it costs almost nothing, survives page reloads, and makes the flagship chart look populated in a demo, which is the stated goal.

### B3. Medium — Trade mechanics are underspecified for a spec whose whole point is trade correctness

Section 8 gives `POST /api/portfolio/trade` a request body and nothing else. Undefined:

- Which price fills the order (cache price at request time, presumably) and what happens when it is `None`.
- The `avg_cost` recomputation formula on a buy-add.
- Whether a sell-to-zero deletes the `positions` row or leaves a zero row. E2E line 453 hedges: "position updates or disappears".
- Rounding. `quantity` and `avg_cost` are REAL (float) and money is float throughout; with fractional shares, repeated buys drift. No decimal-places rule is given, and the prior review's open question 2 on this was never resolved.
- Validation for `quantity <= 0`, NaN, or absurd magnitudes.
- Whether shorting is allowed (selling more than owned) — section 12 lists it as an edge case to test but never states the expected behavior.

Recommendation: add a short "Trade execution rules" subsection with the avg-cost formula, a rounding rule (round money to 2 dp, quantity to 4 dp, at the API boundary), explicit rejection of `quantity <= 0` and oversell, and the zero-position deletion rule. This is cheap to write and eliminates the largest source of frontend/backend disagreement.

### B4. Medium — Response and error schemas are absent

I concur with the prior review's point 3. Adding one worked request/response example per endpoint plus a single canonical error envelope (`{"error": {"code": ..., "message": ...}}`) is the highest return-per-word change available to this document. Chat is the sharpest case: PLAN.md line 328 says a failed trade's error "is included in the chat response" without saying whether it goes into the `actions` JSON, the `message` text, or a separate field, and whether the LLM is re-invoked to explain it or the backend appends a note.

### B5. Medium — SPA fallback routing and static mount order

I concur with the prior review's point 4, and add a concrete constraint: the catch-all static mount at `/` must be registered **after** all `/api/*` routers or it will shadow them, and it must not swallow `/api/*` 404s (an unknown API path should return JSON 404, not `index.html`). Worth one sentence in section 11 because it is a classic single-container FastAPI mistake.

---

## C. Design and safety issues in the plan itself

### C1. High — Auto-execution guardrails, sharpened

The prior review flagged this well (its point 1). I add one observation it missed: the risk is not only that the model errs, it is that **the plan instructs it to act unprompted**. Line 336, "Manage the watchlist proactively", combined with line 323's no-confirmation auto-execution, means the assistant is licensed to mutate state when the user only asked a question. Combined with A7 (any string is a valid ticker), a single hallucination becomes a persisted watchlist entry with a fabricated price.

Recommendation: beyond the prior review's limits (max trades per response, max notional, allowlist), add two rules: (1) trades execute only when the user's message expresses intent or agreement — analysis-only questions must not produce trades; (2) cap `watchlist_changes` per response and forbid removals of tickers with open positions (ties to A2).

### C2. Medium — `portfolio_snapshots` grows without bound and has no read contract

30 s cadence = 2,880 rows/day, forever, on a volume-persisted DB, with `GET /api/portfolio/history` (line 261) specifying no range, limit, or downsampling. A container left running for a week returns 20k points to a line chart.

Recommendation: give the endpoint `?range=` and a documented downsampling or retention rule (e.g. keep 24 h at 30 s, then hourly). One sentence in section 7 and one in section 8.

### C3. Medium — Chat history bound is undefined

Line 293, "Loads recent conversation history". Undefined N, undefined truncation, no token budget. With `gpt-oss-120b` and portfolio context injected on every turn, an unbounded history will eventually fail or get expensive. Specify a concrete window (e.g. last 20 messages) and state that it is truncated oldest-first.

### C4. Medium — Concurrency and lazy-init races

I concur with the prior review's points 2 and 7. Adding specifics: the plan should mandate a single writer connection or a per-trade `BEGIN IMMEDIATE` transaction, WAL mode, and a `busy_timeout`. The lazy-init race is largely moot if the plan adopts B1's lifespan-based startup init (initialize once in lifespan, not per-request), and single-process uvicorn should be stated explicitly since the in-memory `PriceCache` and background task are **incompatible with multiple workers** — with `--workers 2` each worker runs its own simulator and clients see different prices depending on which worker serves the SSE connection. That constraint is currently nowhere in the plan and is easy for a deployment agent to violate.

### C5. Low — `/api/health` should report data-source liveness

The connection dot (line 37) and Docker health both benefit from knowing whether prices are actually flowing. Suggest health returns `{"status", "market_source": "simulator|massive", "tickers": n, "last_update_age_s": x}`. Trivial given `PriceCache`, and it makes A4's silent-stream problem diagnosable.

### C6. Low — Skill name in the plan is wrong

Line 284 says "use cerebras-inference skill" (twice, also line 295). The skill available in this environment is named **`cerebras`**. Since PLAN.md is injected into agent context in full via `CLAUDE.md`, a wrong skill name is a real defect, not a typo. Fix both references.

### C7. Low — Test strategy gaps

I concur with the prior review's point 8 and add three that matter given the code as built: a test that the SSE endpoint mounts once in an app-factory (A6); a test that portfolio valuation survives a watchlist removal (A2); and a test that unknown-ticker handling matches the documented policy in both sources (A7).

---

## D. Repository and documentation accuracy

These are small, verified, and cheap to fix.

1. **`.gitignore` does not ignore the database.** PLAN.md line 102 states "finally.db is gitignored". `.gitignore` contains only the Django-template `db.sqlite3` (line 61) — there is no `*.db`, `db/*.db`, or `db/finally.db` rule. As written, the runtime database would be committed. Add `db/*.db`.
2. **`.env.example` does not exist.** PLAN.md line 105 says it is committed and `README.md` opens its Quick Start with `cp .env.example .env`, which fails today. Create it from section 5.
3. **`db/.gitkeep` does not exist**, so the volume mount target is not in the repo as line 102 requires.
4. **The Docker volume description contradicts itself.** Line 399 uses a *named volume* (`-v finally-data:/app/db`) while line 402 says "The `db/` directory in the project root maps to `/app/db`". Those are mutually exclusive. A named volume does not touch the project directory. Pick one — a bind mount (`-v "$PWD/db:/app/db"`) is friendlier for a course since students can inspect and delete the file, and it is what the directory structure in section 4 implies.
5. **`rich` is a production dependency** (`pyproject.toml:12`) but is used only by `market_data_demo.py`. Minor image bloat; move to the dev extra or accept and note it.

---

## E. Agreement with `planning/review.md`

That review is sound and I agree with all eight of its findings; the strongest are its points 1, 2, and 3. I did not duplicate its analysis where I had nothing to add — see C1 (extends its point 1), C4 (extends 2 and 7), B4 (concurs with 3), B5 (concurs with 4), C7 (concurs with 8). Its point 5 (the `OPENROUTER_API_KEY` "Required" vs. `LLM_MOCK` contradiction) is correct and trivially fixable; A8 above adds that the env loading mechanism itself is misdescribed.

Its main blind spot is that it reviewed the plan as a standalone document and did not check it against the code that already exists. Everything in section A of this review falls in that gap, and A1, A2, and A3 are, in my assessment, more likely to cost real debugging time than anything in the plan's abstract sections — they are already true in the repository today.

Its three open questions are still open. My suggested answers: (1) synchronous within `POST /api/chat` — the plan's own rationale at line 299 supports it and queuing adds a state machine for no user benefit; (2) yes, bound quantity to 4 dp and money to 2 dp, rounded at the API boundary (see B3); (3) a bounded in-memory ring buffer rather than SQLite tick history (see B2).

---

## Prioritized recommendations

Do these before any further agent starts building:

1. Name the ASGI entrypoint and the startup/lifespan sequence (B1). Nothing else can be built or containerized without it.
2. Define the ticker lifecycle invariant: tracked = watchlist ∪ positions; watchlist endpoints drive `add_ticker`/`remove_ticker`; no removal while a position is open (A2, A7).
3. Replace the SSE description with the actual payload, plus heartbeat and flash-on-change semantics (A4, A5).
4. Resolve "daily change %" — add an open/prev-close anchor or rename the column (A1).
5. Decide and document price durability across restarts (A3).
6. Add the "Trade execution rules" subsection: fill price, avg-cost formula, rounding, rejection cases, zero-position handling (B3).
7. Add the LLM execution policy, including intent-gating and watchlist caps (C1).
8. Decide the main chart's data source (B2).
9. Add request/response and error examples per endpoint (B4).
10. Fix the documentation defects in section D and the `cerebras` skill name (C6).

Implementation fix, independent of the plan: make `router` local to `create_stream_router` (A6).
