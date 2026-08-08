# Market Data Backend — Code Review

**Scope:** `backend/app/market/` and `backend/tests/market/`, reviewed against
`planning/MARKET_DATA_DESIGN.md`, `MARKET_INTERFACE.md`, `MARKET_SIMULATOR.md`,
and `MASSIVE_API.md`. `planning/archive/` and `backend/archive/` were excluded
per instructions. Reviewed on branch `week3day2`.

## Verdict

**Solid, ready to build on.** The implementation matches the design docs
closely — in one respect it's ahead of them (see §3). All 94 tests pass, and
the parts of the model that make the biggest engineering claims (GBM
positivity, correlation, determinism, cache-owns-direction) are independently
verifiable and hold up. Findings below are minor: two small test-coverage
gaps, a handful of formatting/lint nits, and one un-load-bearing doc
inaccuracy. Nothing here should block moving on to the next component.

## 1. Test Results

```
94 passed in 3.46s
```

Ran 3 times back-to-back with no flakiness. Coverage:

```
Name                        Stmts   Miss  Cover   Missing
---------------------------------------------------------
app/__init__.py                 0      0   100%
app/market/__init__.py          6      0   100%
app/market/cache.py            19      0   100%
app/market/factory.py          14      2    86%   17-18
app/market/feed.py             60      1    98%   75
app/market/interface.py        10      0   100%
app/market/massive.py          24      0   100%
app/market/models.py           28      0   100%
app/market/seed_prices.py      19      0   100%
app/market/simulator.py        45      2    96%   75-76
app/market/stream.py           28      1    96%   59
---------------------------------------------------------
TOTAL                         253      6    98%
```

The test suite is genuinely good, not just high-coverage: it tests the things
that are easy to get subtly wrong (frozen dataclasses, `change_percent`
division-by-zero, `hashlib` vs. salted `hash()` stability, correlation
ordering, backoff capping, cancellation semantics) rather than just exercising
lines.

## 2. Lint / Format

`uv run ruff check app/ tests/` (the command in `backend/README.md`):

- **1 finding** — `tests/market/test_massive.py:1`: `UTC` imported but
  unused (`F401`). Trivial, auto-fixable with `ruff check --fix`.

`uv run ruff format --check app/ tests/`:

- **3 files** would be reformatted: `app/market/feed.py` (missing blank line
  before `_run`), `app/market/simulator.py` and `tests/market/test_simulator.py`
  (a couple of lines exceed the formatter's wrap width even though
  `E501` is ignored by the linter — `ruff format` and `ruff check` disagree
  here, which is expected since they're independent tools).

None of this is functionally meaningful; it just means `ruff format` hasn't
been run since the last edit to those three files.

## 3. Design Fidelity

The implementation matches the design docs closely, with one deliberate
improvement: `MARKET_INTERFACE_COPARISON.md` (§"Notable Specification Gap")
flagged that the documented `MarketFeed`/factory code only logged generic
exceptions and didn't actually implement the documented 401/403-fallback or
429-backoff policy. The shipped `feed.py` closes that gap — it now has
`FALLBACK_STATUS_CODES`, a `fallback_factory` hook, and exponential backoff
capped at `MAX_POLL_INTERVAL = 60.0`, all covered by
`TestMarketFeedFallback`/`TestMarketFeedBackoff` in `test_feed.py`. Git
history confirms this was addressed in a follow-up review pass
(`f89aa14 Fix all issues from market data code review` and later
`Potential fix for pull request finding` commits).

One thing to flag for whoever wires up FastAPI next: **the fallback capability
is currently inert.** Nothing in the codebase yet constructs a
`MarketFeed(create_source(), cache, tickers, fallback_factory=...)` with a
real fallback — that wiring belongs in the `lifespan` handler described in
`MARKET_DATA_DESIGN.md` §10, which doesn't exist yet (expected, since only the
market data component has been built so far). When that lifespan code is
written, pass `fallback_factory=SimulatorSource` explicitly or the documented
401/403 auto-fallback behavior won't actually trigger in production.

`stream.py` also turns out to satisfy a design requirement "for free": the
design doc says "a comment heartbeat every 15s should be added to keep idle
connections and intermediate proxies alive," and no code in `stream.py`
implements one explicitly. But `sse_starlette.EventSourceResponse` (the
library in use, v3.4.8) defaults `ping_interval` to 15 seconds and sends a
`: ping` comment automatically — confirmed by reading
`sse_starlette/sse.py:259,316`. The requirement is met by the library
default; worth a one-line comment in `stream.py` noting this is intentional,
so a future reader doesn't "fix" it by adding a redundant heartbeat.

## 4. Findings

### Minor — untested code paths

- **`simulator.py:75-76` (`_event_multiplier`'s actual jump branch) has no
  direct test.** Every statistical test disables `EVENT_PROBABILITY` (correctly,
  per the documented rationale that events swamp diffusion statistics), but
  as a result nothing in the suite ever forces an event and asserts its
  magnitude is within `[EVENT_MIN, EVENT_MAX]` or that direction is
  randomized. I verified manually that a forced event produces a plausible
  multiplier (e.g. `1.02` for one seed), so the code is correct — this is a
  coverage gap, not a bug. A test that monkeypatches `source._rng.random` to
  force the branch and asserts the returned multiplier bounds would close it
  and is cheap to add.
- **`factory.py:17-18` (invalid `MARKET_POLL_INTERVAL` → `ValueError` →
  default 15.0) has no test.** The `try/except ValueError` defensive
  handling is a good addition beyond the design doc's literal code sample,
  but nothing exercises `MARKET_POLL_INTERVAL=not-a-number`.
- **`feed.py:75`** (`except asyncio.CancelledError: raise` inside `_tick`) is
  unreached — cancellation in the tests always lands inside `asyncio.sleep`
  in `_run`, not inside a `_tick()` awaited directly. Fine as defensive code;
  not worth a contrived test just to hit the line.

### Minor — robustness not covered by tests

- **`MarketFeed.start()` is not idempotent.** Calling `start()` twice
  overwrites `self._task` without cancelling the previous task, leaking a
  background task that will keep polling and writing into the cache
  alongside the new one. There's exactly one call site today (the future
  `lifespan` handler), so this is low risk, but since `MarketFeed` is public
  API (`app/market/__init__.py`), consider either guarding against a
  double-start (raise or no-op) or documenting that it's the caller's
  responsibility to call it once.

### Nit — stale docstring

- `market_shock` comment math in `test_market_shock_is_shared_across_tickers_in_one_fetch`
  is correct and a nice indirect test, but its docstring says it's verified
  "via a beta=1 ticker pair" — no test in the file actually configures a
  `beta=1` ticker; it counts RNG draws instead (a stronger, more direct
  check). The comment describes an earlier version of the test. Purely
  cosmetic — the test itself is fine and arguably better than what the
  comment describes.

## 5. What I checked and didn't find problems with

- **GBM positivity**: structurally guaranteed by `exp(...)`; confirmed no
  `max(price, ...)` clamp exists anywhere, matching the design's claim.
- **Correlation mechanism**: one `market_shock` drawn per `fetch`, shared
  across tickers via `beta`; independently reran the seeded statistics tests
  three times with no flakiness (seeds are fixed, so this is expected, but
  confirms no hidden nondeterminism e.g. dict ordering).
- **`hashlib` vs. `hash()` for unknown tickers**: correctly uses `hashlib.md5`,
  test explicitly re-derives the expected value independently rather than
  just calling `profile_for` twice (which would pass even if it silently
  regressed to the salted builtin, since both calls happen in the same
  process).
- **Cache "owns direction" invariant**: `Quote` has no `previous_price` field;
  only `PriceCache.apply` can produce a `PriceUpdate`. Structurally, sources
  cannot disagree about direction — matches the design's stated goal.
- **Massive fallback ladder and zero-value window**: `_extract_price`
  matches the documented `lastTrade → min → day → prevDay` order exactly, and
  the zero-value edge case (all fields `0`) correctly resolves to `None` via
  the walrus-guarded comprehension, dropping the ticker rather than
  reporting a `$0.00` quote.
- **SSE payload shape**: `stream.py` explicitly JSON-encodes `data` rather
  than relying on `sse_starlette`'s dict handling, with a regression test
  guarding against the single-quoted Python-repr failure mode. Good catch by
  whoever wrote this — that's an easy thing to get wrong silently, since it
  only breaks in the browser, not in a Python test that doesn't parse the
  wire format.
- **No network access in tests**: confirmed via `grep` — every `MassiveSource`
  test goes through `httpx.MockTransport`; no test suite dependency on
  outbound connectivity.

## 6. Recommendation

Ship it as-is. Suggested follow-ups, roughly in priority order, none of which
need to block starting the next component:

1. `uv run ruff check --fix tests/market/test_massive.py` and
   `uv run ruff format app/market/feed.py app/market/simulator.py tests/market/test_simulator.py`
   — thirty seconds, zero risk.
2. Add the two missing unit tests noted in §4 (forced drama event, invalid
   `MARKET_POLL_INTERVAL`) — cheap, closes the only real coverage gaps.
3. When writing the FastAPI `lifespan` wiring, remember to pass
   `fallback_factory=SimulatorSource` to `MarketFeed` so the documented
   401/403 auto-fallback is actually live, and consider guarding
   `MarketFeed.start()` against being called twice.
