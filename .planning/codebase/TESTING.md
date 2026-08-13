# Testing Patterns

**Analysis Date:** 2026-08-12

## Test Framework

**Test Runner:**
- pytest >= 8.3.0
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Async Testing:**
- pytest-asyncio >= 0.24.0
- Mode: `asyncio_mode = "auto"` (auto-detects async test functions)
- Scope: `asyncio_default_fixture_loop_scope = "function"` (new event loop per test)

**Coverage:**
- pytest-cov >= 5.0.0
- Source tracked: `app/` (test code excluded)
- Exclude patterns: `pragma: no cover`, `__repr__`, `NotImplementedError`, `__main__`, `TYPE_CHECKING`

**Run Commands:**
```bash
uv run pytest -v              # All tests
uv run pytest --cov=app       # With coverage report
uv run pytest -k test_name    # Single test by name
uv run pytest tests/market/   # Single module
uv run ruff check app/ tests/ # Lint before/after
```

## Test File Organization

**Location:**
- Tests live in `tests/` directory mirroring `app/` structure
- Example: `app/market/simulator.py` → `tests/market/test_simulator.py`
- Each test module gets one `test_*.py` file per source module

**Directory Structure:**
```
backend/
├── app/
│   ├── market/
│   │   ├── __init__.py
│   │   ├── interface.py
│   │   ├── simulator.py
│   │   └── cache.py
│   └── ...
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── market/
│   │   ├── __init__.py
│   │   ├── test_interface.py
│   │   ├── test_simulator.py
│   │   └── test_cache.py
│   └── ...
```

**Naming Convention:**
- Test files: `test_*.py`
- Test classes: `Test*` (e.g., `TestSimulatorSource`, `TestPriceCacheApply`)
- Test functions: `test_*` (e.g., `test_same_seed_produces_identical_price_sequence`)

## Test Structure

**Class-Based Organization:**
- Group tests into classes by feature or method
- Each class tests one aspect of the module
- Example from `tests/market/test_simulator.py`:
  - `TestSimulatorSourceDeterminism` — tests seeding behavior
  - `TestSimulatorSourcePositivity` — tests price invariants
  - `TestSimulatorSourceFetch` — tests the fetch contract
  - `TestSimulatorSourceEvents` — tests dramatic event multipliers
  - `TestSimulatorSourceStatistics` — tests statistical properties

**Arrange-Act-Assert Pattern:**
```python
async def test_same_seed_produces_identical_price_sequence(self):
    # Arrange
    a = SimulatorSource(seed=42)
    b = SimulatorSource(seed=42)

    # Act
    for _ in range(50):
        quotes_a = await a.fetch(["AAPL", "GOOGL"])
        quotes_b = await b.fetch(["AAPL", "GOOGL"])
    
    # Assert
        assert [q.price for q in quotes_a] == [q.price for q in quotes_b]
```

**Direct Assertions:**
- Use `assert condition` (not self.assert* helpers)
- Assertions should be clear and specific

**Helper Functions:**
- Create test data helpers at module scope, prefix with `_`
- Example from `tests/market/test_simulator.py`:
  ```python
  def _quote(ticker: str, price: float) -> Quote:
      return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))
  ```

## Pytest Fixtures & Conftest

**Shared Fixtures:**
- Location: `tests/conftest.py`
- Example: autouse fixture that cleans environment variables before each test
  ```python
  @pytest.fixture(autouse=True)
  def _clean_market_env(monkeypatch):
      """Every test starts with no market-related environment variables set."""
      for var in ("MASSIVE_API_KEY", "MARKET_POLL_INTERVAL", "MARKET_SEED"):
          monkeypatch.delenv(var, raising=False)
  ```

**Built-in Fixtures Used:**
- `monkeypatch` — patch environment variables, module attributes, functions
- No custom fixtures yet (may add in later phases for database, app context, etc.)

## Async Testing Patterns

**Async Test Functions:**
- Mark with `async def test_*`
- Pytest-asyncio automatically detects and awaits them
- Example:
  ```python
  async def test_prices_always_positive(self):
      source = SimulatorSource(seed=123)
      for _ in range(2000):
          quotes = await source.fetch(["AAPL", "TSLA"])
          assert all(q.price > 0 for q in quotes)
  ```

**Testing Async Generators:**
- Use `anext()` to fetch next item from async generator
- Use `await gen.aclose()` for cleanup
- Example from `tests/market/test_stream.py`:
  ```python
  async def test_new_subscriber_gets_full_snapshot_first(self):
      cache = PriceCache()
      cache.apply([_quote("AAPL", 190.0), _quote("GOOGL", 175.0)])

      gen = price_events(cache)
      first = json.loads((await anext(gen))["data"])
      second = json.loads((await anext(gen))["data"])

      emitted_tickers = {first["ticker"], second["ticker"]}
      assert emitted_tickers == {"AAPL", "GOOGL"}
      await gen.aclose()
  ```

**Testing Background Tasks:**
- Test the `_tick()` or `_run()` method directly, don't wrap in task
- Example from `tests/market/test_feed.py`:
  ```python
  async def test_transient_failure_does_not_stop_the_loop(self):
      source = FakeSource(behaviors=[RuntimeError("upstream down")])
      cache = PriceCache()
      feed = MarketFeed(source, cache, lambda: ["AAPL"])

      await feed._tick()  # First tick fails
      await feed._tick()  # Second tick recovers
      assert cache.get("AAPL") is not None
  ```

## Mocking & Test Doubles

**Monkeypatch for Env Vars:**
- Example:
  ```python
  async def test_env_seed_is_used_when_no_explicit_seed(self, monkeypatch):
      monkeypatch.setenv("MARKET_SEED", "7")
      a = SimulatorSource()
      b = SimulatorSource(seed=7)
      # Assert they produce identical sequences
  ```

**Monkeypatch for Method/Attribute Patching:**
- Replace RNG method to control test behavior:
  ```python
  def test_triggered_event_jumps_upward_within_bounds(self, monkeypatch):
      source = SimulatorSource(seed=1)
      random_calls = iter([0.0, 0.0])
      monkeypatch.setattr(source._rng, "random", lambda: next(random_calls))
      monkeypatch.setattr(source._rng, "uniform", lambda lo, hi: EVENT_MAX)

      assert source._event_multiplier() == pytest.approx(1 + EVENT_MAX)
  ```

**HTTP Mocking:**
- Use httpx.MockTransport for testing HTTP clients
- Example from `tests/market/test_massive.py`:
  ```python
  def _client(handler) -> httpx.AsyncClient:
      transport = httpx.MockTransport(handler)
      return httpx.AsyncClient(
          base_url="https://api.massive.com",
          headers={"Authorization": "Bearer test-key"},
          transport=transport,
      )
  
  async def test_parses_snapshot_into_quotes(self):
      def handler(request):
          return _snapshot_response([
              {"ticker": "AAPL", "lastTrade": {"p": 190.5}},
              {"ticker": "GOOGL", "lastTrade": {"p": 175.25}},
          ])
      
      source = MassiveSource("test-key", client=_client(handler))
      quotes = await source.fetch(["AAPL", "GOOGL"])
      assert [(q.ticker, q.price) for q in quotes] == [("AAPL", 190.5), ("GOOGL", 175.25)]
  ```

**Custom Test Doubles:**
- Implement the same interface as production code for testability
- Example: `FakeSource` in `tests/market/test_feed.py` implements `MarketDataSource`
  ```python
  class FakeSource(MarketDataSource):
      """A source whose behaviour per call is scripted by the test."""
      
      def __init__(self, name="fake", poll_interval=15.0, behaviors=None):
          self.name = name
          self.poll_interval = poll_interval
          self._behaviors = list(behaviors or [])
          self.fetch_calls = 0
          self.closed = False

      async def fetch(self, tickers):
          self.fetch_calls += 1
          if self._behaviors:
              behavior = self._behaviors.pop(0)
              if isinstance(behavior, Exception):
                  raise behavior
              return behavior
          return _quotes(*tickers)

      async def aclose(self):
          self.closed = True
  ```
- Script behavior with a queue: exceptions, lists of quotes, or defaults

## Assertions

**Direct Assertions:**
- `assert condition` for boolean checks
- `assert actual == expected` for equality
- `assert actual in expected` for membership

**Floating Point Comparison:**
- Use `pytest.approx()` for float tolerance
- Example:
  ```python
  assert update.change == pytest.approx(10.0)
  assert realized_sigma == pytest.approx(configured_sigma, rel=0.35)
  ```

**Type Checking:**
- Use `isinstance()` for type checks:
  ```python
  def test_unset_key_selects_simulator(self, monkeypatch):
      monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
      assert isinstance(create_source(), SimulatorSource)
  ```

**Exception Testing:**
- Use `pytest.raises()` context manager:
  ```python
  def test_is_frozen(self):
      quote = Quote(ticker="AAPL", price=190.0, timestamp=datetime.now(UTC))
      with pytest.raises(AttributeError):
          quote.price = 200.0
  ```

**Membership/Set Checks:**
- Use set operations for clean comparisons:
  ```python
  def test_returns_all_known_tickers(self):
      cache = PriceCache()
      cache.apply([_quote("AAPL", 190.0), _quote("GOOGL", 175.0)])

      tickers = {u.ticker for u in cache.snapshot()}
      assert tickers == {"AAPL", "GOOGL"}
  ```

**JSON/Data Structure Validation:**
- Validate data format and keys:
  ```python
  async def test_event_shape(self):
      cache = PriceCache()
      cache.apply([_quote("AAPL", 190.0)])

      gen = price_events(cache)
      event = await anext(gen)

      assert event["event"] == "price"
      data = json.loads(event["data"])
      assert set(data) == {
          "ticker", "price", "previous_price", "change",
          "change_percent", "direction", "timestamp",
      }
      await gen.aclose()
  ```

## Test Coverage

**Coverage Configuration (pyproject.toml):**
```toml
[tool.coverage.run]
source = ["app"]
omit = ["tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

**View Coverage:**
```bash
uv run pytest --cov=app --cov-report=html  # HTML report in htmlcov/
uv run pytest --cov=app --cov-report=term-missing  # Show uncovered lines
```

**No enforced minimum** (yet). Target: high coverage for market data (simulator, cache, feed are critical).

## Test Data & Fixtures

**Simple Test Data:**
- Use helper functions for common object construction:
  ```python
  def _quote(ticker: str, price: float) -> Quote:
      return Quote(ticker=ticker, price=price, timestamp=datetime.now(UTC))
  
  def _update(price: float, previous_price: float) -> PriceUpdate:
      return PriceUpdate(
          ticker="AAPL",
          price=price,
          previous_price=previous_price,
          timestamp=datetime.now(UTC),
      )
  ```

**Response Fixtures:**
- Mock HTTP responses with helper functions:
  ```python
  def _snapshot_response(tickers: list[dict]) -> httpx.Response:
      return httpx.Response(
          200,
          json={"status": "OK", "count": len(tickers), "tickers": tickers}
      )
  ```

## Test Types & Scope

**Unit Tests:**
- Test individual classes/functions in isolation
- Use mocks/doubles for dependencies
- Fast to run (~milliseconds each)
- Example: `TestPriceCacheApply` tests cache state transitions without a feed

**Integration Tests:**
- Test multiple components working together
- Example: `TestMarketFeedResilience` tests feed + cache + source coordination
- Still use mocks for external services (HTTP) but test the glue layer

**Statistical/Behavioral Tests:**
- Validate emergent properties after many iterations
- Example: `TestSimulatorSourceStatistics` verifies GBM volatility and correlation
- More expensive, fewer of them

**E2E Tests:**
- Not yet in codebase (will use Playwright in `test/` when frontend exists)
- Will test full app with real Docker container

## Common Test Patterns

**Testing Deterministic Behavior:**
```python
async def test_same_seed_produces_identical_price_sequence(self):
    a = SimulatorSource(seed=42)
    b = SimulatorSource(seed=42)

    for _ in range(50):
        quotes_a = await a.fetch(["AAPL", "GOOGL"])
        quotes_b = await b.fetch(["AAPL", "GOOGL"])
        assert [q.price for q in quotes_a] == [q.price for q in quotes_b]
```

**Testing Invariants (Properties):**
```python
async def test_prices_always_positive(self):
    source = SimulatorSource(seed=123)
    tickers = ["AAPL", "TSLA", "NVDA", "JPM"]

    for _ in range(2000):
        quotes = await source.fetch(tickers)
        assert all(q.price > 0 for q in quotes)
```

**Testing Error Handling & Fallback:**
```python
async def test_401_falls_back_to_fallback_source(self):
    primary = FakeSource(name="massive", behaviors=[_http_error(401)])
    fallback_source = FakeSource(name="simulator")
    cache = PriceCache()
    feed = MarketFeed(primary, cache, lambda: ["AAPL"], fallback_factory=lambda: fallback_source)

    await feed._tick()

    assert feed.source is fallback_source
    assert primary.closed is True
```

**Testing Sequential State Changes:**
```python
async def test_rise_yields_up(self):
    cache = PriceCache()
    cache.apply([_quote("AAPL", 190.0)])  # First state
    changed = cache.apply([_quote("AAPL", 195.0)])  # Transition

    assert len(changed) == 1
    assert changed[0].direction == "up"
    assert changed[0].previous_price == 190.0
    assert changed[0].price == 195.0
```

**Testing Edge Cases & Boundaries:**
```python
def test_change_percent_zero_previous_price_does_not_divide_by_zero(self):
    update = _update(price=5.0, previous_price=0.0)
    assert update.change_percent == 0.0  # Not NaN, not infinity

def test_empty_ticker_list_returns_empty_without_request(self):
    called = False

    def handler(request):
        nonlocal called
        called = True
        return _snapshot_response([])

    source = MassiveSource("test-key", client=_client(handler))
    assert await source.fetch([]) == []
    assert called is False  # No HTTP request made
```

---

*Testing analysis: 2026-08-12*
