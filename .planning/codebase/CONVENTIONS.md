# Coding Conventions

**Analysis Date:** 2026-08-12

## Naming Patterns

**Files:**
- Python modules: `lowercase_with_underscores.py` (e.g., `market_feed.py`, `simulator.py`)
- Test files: `test_*.py` (e.g., `test_simulator.py`, `test_cache.py`)
- Factory files: `factory.py` (e.g., `app/market/factory.py`)

**Functions & Methods:**
- Snake_case: `create_source()`, `apply()`, `fetch()`, `_advance()`, `_handle_http_error()`
- Private functions/methods: prefixed with `_` (e.g., `_event_multiplier()`, `_format()`, `_extract_price()`)
- Async functions: same convention with `async def` (e.g., `async def fetch()`)

**Variables & Parameters:**
- Snake_case: `poll_interval`, `market_shock`, `cache_key`, `_rng`
- Instance attributes: prefixed with `_` when private (e.g., `self._prices`, `self._source`)
- Loop variables: descriptive where possible (e.g., `for update in cache.snapshot()`)

**Types & Classes:**
- PascalCase for classes: `MarketDataSource`, `SimulatorSource`, `PriceCache`, `Quote`, `PriceUpdate`
- Abstract base classes: `MarketDataSource` (interface), concrete implementations: `SimulatorSource`, `MassiveSource`
- Dataclasses: frozen immutable types (e.g., `Quote`, `PriceUpdate`, `TickerProfile`)

**Constants:**
- UPPER_CASE: `TRADING_SECONDS_PER_YEAR`, `TICK_SECONDS`, `MAX_POLL_INTERVAL`, `FALLBACK_STATUS_CODES`
- Module-level constants grouped near top of file, before class definitions

## Code Style

**Formatting:**
- Line length: 100 characters (ruff configured, E501 ignored)
- Target Python version: 3.12
- No formatter enforced (black/autopep8 not in dependencies); style via linting only

**Linting:**
- Tool: ruff (`ruff>=0.7.0`)
- Rules enabled: E (pycodestyle errors), F (Pyflakes), I (isort), N (pep8-naming), W (pycodestyle warnings)
- Configuration in `pyproject.toml`: `[tool.ruff]` and `[tool.ruff.lint]`
- Example: `ruff check app/ tests/`

## Type Hints

**Usage:**
- Type hints required on all function signatures and method definitions
- Return types always specified: `-> list[Quote]`, `-> None`, `-> float | None`
- Union types use modern syntax: `str | None`, `dict[str, float]`, not `Optional[T]` or `Union[T, U]`
- Async iterators typed: `AsyncIterator[dict]`

**Examples from codebase:**
```python
async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
    """Fetch prices for requested tickers."""
    ...

def _extract_price(item: dict) -> float | None:
    """Extract price from snapshot item."""
    ...

def __init__(self, seed: int | None = None) -> None:
    ...
```

## Import Organization

**Order:**
1. Standard library (`import os`, `from datetime import UTC`)
2. Third-party (`import httpx`, `from fastapi import APIRouter`)
3. Local/internal (`from .interface import MarketDataSource`, `from app.market import Quote`)
4. Blank line between each group

**Path Aliases:**
- Relative imports within same package: `from .cache import PriceCache`
- Absolute imports from app root: `from app.market import Quote`
- No package-level `__init__` imports except in `__all__` exports

**Example from `app/market/stream.py`:**
```python
import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from .cache import PriceCache
from .models import PriceUpdate
```

## Docstrings

**Module docstrings:**
- One-liner describing the module's purpose at the top: `"""The unified market data source contract."""`
- Can include architectural notes for complex modules

**Class docstrings:**
- Multi-line for non-trivial classes
- Include a "Contract" section for abstract base classes or classes with special invariants
- Document thread safety if relevant (e.g., `PriceCache` notes single-writer model)

**Example from `app/market/interface.py`:**
```python
class MarketDataSource(ABC):
    """Abstract source of current prices for a set of tickers.

    Contract:
      - `fetch` is async and must not block the event loop.
      - `fetch` is stateless with respect to the caller.
      - `fetch` may return fewer quotes than requested.
      - `fetch` raises only on total failure (network down, auth rejected).
      - `poll_interval` is advisory and read by the feed.
    """
```

**Function/Method docstrings:**
- One-liner for simple functions: `"""Release any held resources. Overridden where needed."""`
- Multi-line for complex logic or side effects
- Use active voice, imperative mood: "Advance every requested ticker one tick" not "Advances..."

**Dataclass field docstrings:**
- Document field purpose as docstring under field definition:
```python
@dataclass(frozen=True, slots=True)
class TickerProfile:
    anchor: float
    """Price the random walk is pulled back toward."""
    
    volatility: float
    """Annualised volatility, e.g. 0.28 for 28%."""
```

**Inline comments:**
- Sparingly used; explain *why*, not *what*
- Example: `# hashlib not hash() — Python salts hash() for strings with per-process seed`
- Example: `# log space to guarantee positivity in GBM`

## Error Handling

**Patterns:**

**Specific exception catching** — catch only what you can handle:
```python
try:
    quotes = await self._source.fetch(self._tickers())
except httpx.HTTPStatusError as exc:
    await self._handle_http_error(exc)
except asyncio.CancelledError:
    raise  # Always re-raise CancelledError
except Exception:
    logger.exception("market fetch failed, serving cached prices")
```

**Logging on errors:**
- `logger.exception(msg)` — logs stack trace at ERROR level
- `logger.warning(msg)` — for degraded but recoverable conditions
- Include context: `logger.error("market source %r rejected (HTTP %s)", name, status)`

**Defensive defaults:**
- Use `.get()` with sensible defaults: `self._prices.get(ticker, profile.anchor)`
- Early returns for edge cases: `if not tickers: return []`
- Fall-through chains for graceful degradation (e.g., `_extract_price` in `app/market/massive.py`)

**No defensive coding without reason:**
- Don't catch exceptions you don't understand
- Don't add null checks where contracts guarantee non-null
- Example: `PriceCache.apply()` doesn't check if quote is None because `Quote` is required parameter

## Data Models

**Dataclasses:**
- Use `frozen=True` for immutable data (required for hashability, safety):
  ```python
  @dataclass(frozen=True, slots=True)
  class Quote:
      ticker: str
      price: float
      timestamp: datetime
  ```
- Use `slots=True` for memory efficiency
- All dataclass fields should have type hints

**Properties:**
- Computed fields implemented as `@property` for cleaner API:
  ```python
  @property
  def direction(self) -> str:
      """One of "up", "down", "flat" — drives the frontend flash colour."""
      if self.price > self.previous_price:
          return "up"
      ...
  ```

## Async/Await Patterns

**Async functions:**
- Always mark with `async def`: `async def fetch(self, tickers: Sequence[str])`
- Use `await` for async operations: `await self._source.fetch(...)`
- Async context managers for cleanup: `async with ... as ...:` (not yet used, but pattern for resources)

**Async generators:**
- Used for streaming: `async def price_events(cache) -> AsyncIterator[dict]:`
- Yield dicts/events, not structured objects for JSON compatibility
- Cleanup with `await gen.aclose()` or catch `asyncio.CancelledError`

**Background tasks:**
- Created with `asyncio.create_task(coro)` (not `asyncio.ensure_future`)
- Cleanup: check if task is done with `task.done()`, cancel with `task.cancel()`, await to consume the `CancelledError`

**Example from `app/market/feed.py`:**
```python
async def _run(self) -> None:
    while True:
        await self._tick()
        await asyncio.sleep(self._source.poll_interval)

def start(self) -> None:
    if self._task is not None and not self._task.done():
        raise RuntimeError("MarketFeed.start() called while already running")
    self._task = asyncio.create_task(self._run())

async def stop(self) -> None:
    task = self._task
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self._task = None
```

## Dependency Injection

**Pattern:**
- Constructor injection (pass dependencies to `__init__`)
- Optional dependencies with defaults: `client: httpx.AsyncClient | None = None`
- Factory functions that encapsulate env-based selection: `create_source()` returns either `MassiveSource` or `SimulatorSource`

**Example from `app/market/stream.py`:**
```python
def create_stream_router(cache: PriceCache) -> APIRouter:
    """Build the `/api/stream/prices` router bound to a specific cache.
    
    A factory (rather than a module-level router reading `request.app.state`)
    keeps this endpoint independently testable without a full app lifespan.
    """
    router = APIRouter()

    @router.get("/api/stream/prices")
    async def stream_prices(request: Request) -> EventSourceResponse:
        return EventSourceResponse(price_events(cache))

    return router
```

## Module Exports

**`__all__` for public APIs:**
- Explicitly define what is exported from a module
- Example from `app/market/__init__.py`:
  ```python
  __all__ = [
      "MarketDataSource",
      "MarketFeed",
      "PriceCache",
      "PriceUpdate",
      "Quote",
      "create_source",
  ]
  ```

## Determinism & Testing

**Seeding for reproducibility:**
- Use `hashlib` instead of built-in `hash()` for stable string→number mapping
- Respect `MARKET_SEED` environment variable for simulator reproducibility
- Example: `profile_for(ticker)` uses `hashlib.md5()` to generate deterministic prices for unknown tickers

---

*Convention analysis: 2026-08-12*
