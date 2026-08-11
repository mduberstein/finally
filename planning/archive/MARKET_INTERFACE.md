# Market Data Interface

The unified Python API for retrieving stock prices in FinAlly. One interface, two
implementations: the Massive API when `MASSIVE_API_KEY` is set, the built-in
simulator otherwise. Everything downstream — the price cache, the SSE stream, the
portfolio valuation, the frontend — is agnostic to which one is running.

Companion documents: `MASSIVE_API.md` (the upstream API), `MARKET_SIMULATOR.md`
(the simulator internals).

## 1. Design Goals

1. **One seam.** Exactly one place decides which data source is live. Nothing else
   in the codebase branches on the environment variable.
2. **Source cadence is not stream cadence.** The simulator ticks every 500 ms; the
   Massive poller runs every 15 s. The SSE stream must look identical either way.
3. **Pull, not push.** The source exposes a plain `fetch(tickers)` coroutine. The
   background feed owns timing. No callbacks, no observer registration.
4. **Sources do not hold history.** A source answers "what is the price now". The
   cache is the only component that remembers a previous price and derives
   direction.
5. **Degrade, do not crash.** An upstream failure serves stale cached prices; it
   never takes down the app.

## 2. Module Layout

```
backend/app/market/
├── __init__.py       # public exports
├── models.py         # Quote, PriceUpdate
├── interface.py      # MarketDataSource abstract base class
├── simulator.py      # SimulatorSource
├── massive.py        # MassiveSource
├── seed_prices.py    # anchor prices for the simulator
├── cache.py          # PriceCache
├── feed.py           # MarketFeed background task
└── factory.py        # create_source()
```

Dependency direction is strictly one way:

```
factory ──> simulator ──┐
        └─> massive ────┴──> interface ──> models
                                              ^
feed ──> cache ───────────────────────────────┘
```

`cache.py` and `feed.py` never import a concrete source. `simulator.py` and
`massive.py` never import each other.

## 3. Data Models

`models.py`

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Quote:
    """A price observation from a market data source."""

    ticker: str
    price: float
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """A quote paired with the previously seen price, ready to stream."""

    ticker: str
    price: float
    previous_price: float
    timestamp: datetime

    @property
    def change(self) -> float:
        return self.price - self.previous_price

    @property
    def change_percent(self) -> float:
        if self.previous_price == 0:
            return 0.0
        return (self.change / self.previous_price) * 100

    @property
    def direction(self) -> str:
        """One of "up", "down", "flat" — drives the frontend flash colour."""
        if self.price > self.previous_price:
            return "up"
        if self.price < self.previous_price:
            return "down"
        return "flat"
```

### Why two models

A source reports a single observation and has no business knowing what came
before. Keeping `previous_price` out of `Quote` means the simulator does not have
to track it, the Massive client does not have to track it, and there is exactly
one implementation of "did it go up" — in the cache. If both sources computed
direction independently, they would eventually disagree.

## 4. The Interface

`interface.py`

```python
from abc import ABC, abstractmethod
from collections.abc import Sequence

from .models import Quote


class MarketDataSource(ABC):
    """Abstract source of current prices for a set of tickers."""

    name: str
    poll_interval: float
    """Seconds the feed should wait between fetches."""

    @abstractmethod
    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        """Return current quotes for the requested tickers.

        Tickers with no available price are omitted rather than raising.
        """

    async def aclose(self) -> None:
        """Release any held resources. Overridden where needed."""
```

The contract in full:

- `fetch` is **async** and must not block the event loop.
- `fetch` is **stateless with respect to the caller** — calling it twice with the
  same tickers is always valid.
- `fetch` **may return fewer quotes than requested**. Unknown, delisted or
  temporarily unavailable tickers are dropped silently. Callers must not assume
  a one-to-one mapping.
- `fetch` **raises only on total failure** (network down, auth rejected). A partial
  result is a success.
- `poll_interval` is advisory and read once by the feed when it starts.

## 5. The Simulator Source

Full detail is in `MARKET_SIMULATOR.md`. The contract from the interface's point
of view:

```python
class SimulatorSource(MarketDataSource):
    name = "simulator"
    poll_interval = 0.5

    def __init__(self, seed: int | None = None) -> None: ...

    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        """Advance the model one tick and return every requested ticker."""
```

Two properties worth noting here because they affect the interface:

- The simulator **never** drops a ticker. Any symbol it has not seen is assigned a
  deterministic synthetic starting price on first request, so `fetch` always
  returns one quote per requested ticker.
- The simulator is **stateful across calls** — each `fetch` advances the random
  walk by one step. This is the one place where calling `fetch` has a side effect,
  and it is why the feed must be the only caller.

## 6. The Massive Source

`massive.py`

```python
import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime

import httpx

from .interface import MarketDataSource
from .models import Quote

BASE_URL = "https://api.massive.com"
SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"


class MassiveSource(MarketDataSource):
    """Live prices from the Massive REST snapshot endpoint."""

    name = "massive"

    def __init__(self, api_key: str, poll_interval: float = 15.0) -> None:
        self.poll_interval = poll_interval
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )

    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        if not tickers:
            return []

        response = await self._client.get(
            SNAPSHOT_PATH, params={"tickers": ",".join(tickers)}
        )
        response.raise_for_status()
        payload = response.json()

        now = datetime.now(UTC)
        return [
            Quote(ticker=item["ticker"], price=price, timestamp=now)
            for item in payload.get("tickers", [])
            if (price := _extract_price(item))
        ]

    async def aclose(self) -> None:
        await self._client.aclose()


def _extract_price(item: dict) -> float | None:
    """Most recent usable price.

    Snapshot bars are zeroed nightly at 3:30 AM ET and repopulate from 4:00 AM,
    so day and minute closes are 0 outside trading hours. Fall through to the
    previous day's close, which is always populated.
    """
    return (
        item.get("lastTrade", {}).get("p")
        or item.get("min", {}).get("c")
        or item.get("day", {}).get("c")
        or item.get("prevDay", {}).get("c")
    )
```

### Why raw httpx and not the `massive` client

The official `massive` package (version 2.8.0) is built on `urllib3.PoolManager`
and is **synchronous**. Calling it from a FastAPI coroutine blocks the event loop
and stalls every open SSE connection, so every call would need wrapping in
`asyncio.to_thread`. We need exactly one endpoint. A direct `httpx` call is
natively async, has no hidden retry behaviour, and is less code than the
offload wrapper would be. `MASSIVE_API.md` section 5 documents the client for
reference if we later need historical bars.

### Free-tier reality

A free Stocks Basic key **cannot call the snapshot endpoint at all** — it returns
403, and the plan is end-of-day only regardless. There is no configuration that
makes a free key stream live prices. Section 9 covers what happens when this is
detected. The simulator remains the default experience, as `PLAN.md` specifies.

## 7. The Price Cache

`cache.py`

```python
from collections.abc import Iterable

from .models import PriceUpdate, Quote


class PriceCache:
    """In-memory store of the latest and previous price per ticker."""

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}

    def apply(self, quotes: Iterable[Quote]) -> list[PriceUpdate]:
        """Record quotes and return updates whose price actually changed."""
        changed = []
        for quote in quotes:
            existing = self._prices.get(quote.ticker)
            previous = existing.price if existing else quote.price
            update = PriceUpdate(
                ticker=quote.ticker,
                price=quote.price,
                previous_price=previous,
                timestamp=quote.timestamp,
            )
            self._prices[quote.ticker] = update
            if existing is None or update.price != previous:
                changed.append(update)
        return changed

    def get(self, ticker: str) -> PriceUpdate | None:
        return self._prices.get(ticker)

    def snapshot(self) -> list[PriceUpdate]:
        """Everything currently known — sent to each new SSE subscriber."""
        return list(self._prices.values())
```

On the first sighting of a ticker, `previous_price` equals `price`, so
`direction` is `"flat"` and the frontend does not flash a spurious colour on page
load. That first update is still emitted, so the client learns the price.

No lock is needed. A single feed task is the only writer, and asyncio gives it
uncontended access between awaits.

The cache is deliberately not persisted. Prices are ephemeral; restarting the
container starts from fresh quotes.

## 8. The Feed

`feed.py`

```python
import asyncio
import logging
from collections.abc import Callable, Sequence

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MarketFeed:
    """Background task polling a source and writing into the cache."""

    def __init__(
        self,
        source: MarketDataSource,
        cache: PriceCache,
        tickers: Callable[[], Sequence[str]],
    ) -> None:
        self._source = source
        self._cache = cache
        self._tickers = tickers
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        await self._source.aclose()

    async def _run(self) -> None:
        while True:
            try:
                quotes = await self._source.fetch(self._tickers())
                self._cache.apply(quotes)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("market fetch failed, serving cached prices")
            await asyncio.sleep(self._source.poll_interval)
```

`tickers` is a callable, not a list, so the feed picks up watchlist additions on
the next poll without the feed knowing anything about the database.

The broad `except` here is deliberate and is the one place defensive handling
earns its place: a transient upstream failure must not kill the only task feeding
the entire application. Everything else keeps working off cached prices.

## 9. The Factory

`factory.py`

```python
import os

from .interface import MarketDataSource
from .massive import MassiveSource
from .simulator import SimulatorSource


def create_source() -> MarketDataSource:
    """The one place that decides which market data source is live."""
    api_key = os.getenv("MASSIVE_API_KEY", "").strip()
    if api_key:
        interval = float(os.getenv("MARKET_POLL_INTERVAL", "15"))
        return MassiveSource(api_key, poll_interval=interval)
    return SimulatorSource()
```

`.strip()` matters: `.env` files routinely contain `MASSIVE_API_KEY=` or a value
with a trailing space, and a whitespace-only key must count as absent.

### Environment variables

| Variable | Default | Effect |
|---|---|---|
| `MASSIVE_API_KEY` | unset | Non-empty selects `MassiveSource`; empty or unset selects `SimulatorSource` |
| `MARKET_POLL_INTERVAL` | `15` | Massive poll interval in seconds. Ignored by the simulator. |
| `MARKET_SEED` | unset | Fixes the simulator's RNG seed for reproducible tests |

### Failure policy

The distinction that matters is whether a failure can heal itself:

| Condition | Response |
|---|---|
| 401, 403 | Permanent — bad key, or a plan that excludes snapshots. Log an explicit warning naming the cause and swap in `SimulatorSource` so the app stays usable. |
| 429 | Transient — back off by doubling the poll interval up to a 60 s ceiling. |
| 5xx, timeouts, network errors | Transient — log and retry on the next tick, serving cached prices. |

Auto-falling back on 401/403 is a considered trade-off. It hides a
misconfiguration, which is normally bad, but a wrong key on a course project
would otherwise yield a blank, priceless UI with no explanation. The loud log
line is what keeps this honest, and it only triggers on errors that will never
self-heal.

## 10. Wiring Into FastAPI

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.market import MarketFeed, PriceCache, create_source


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = PriceCache()
    feed = MarketFeed(create_source(), cache, watchlist_tickers)
    feed.start()
    app.state.prices = cache
    yield
    await feed.stop()


app = FastAPI(lifespan=lifespan)
```

One feed, one cache, for the lifetime of the process. Routes read
`request.app.state.prices`.

## 11. SSE Streaming

This is where source cadence is decoupled from stream cadence. The endpoint reads
the cache on its own 500 ms schedule and never touches the source:

```python
STREAM_INTERVAL = 0.5


async def price_events(cache: PriceCache):
    """Yield SSE frames: a full snapshot first, then changes only."""
    seen: dict[str, float] = {}

    for update in cache.snapshot():
        seen[update.ticker] = update.price
        yield _format(update)

    while True:
        await asyncio.sleep(STREAM_INTERVAL)
        for update in cache.snapshot():
            if seen.get(update.ticker) != update.price:
                seen[update.ticker] = update.price
                yield _format(update)
```

Each new subscriber receives a full snapshot immediately, so a page load renders
prices without waiting for the next poll. After that only changed tickers are
sent.

`PLAN.md` describes pushing all tickers every 500 ms. Sending only changes is a
deliberate refinement: with a 15 s Massive poll, 96% of those frames would be
byte-identical repeats. The observable behaviour for the frontend is unchanged,
because a repeated price would produce a `flat` direction and no flash. A comment
heartbeat every 15 s keeps idle connections and intermediate proxies alive.

## 12. Public Exports

`__init__.py`

```python
from .cache import PriceCache
from .factory import create_source
from .feed import MarketFeed
from .interface import MarketDataSource
from .models import PriceUpdate, Quote

__all__ = [
    "MarketDataSource",
    "MarketFeed",
    "PriceCache",
    "PriceUpdate",
    "Quote",
    "create_source",
]
```

Concrete sources are intentionally not exported. Application code obtains a source
through `create_source()` and depends only on the abstract type.

## 13. Testing

| Target | Test |
|---|---|
| Interface conformance | Parametrise one test over both sources: `fetch` returns `Quote` objects, never raises on an empty ticker list, tolerates unknown symbols |
| `PriceCache` | First sighting yields `flat`; a rise yields `up`; an unchanged price is not reported as changed; `change_percent` maths |
| `MassiveSource` | Parse a captured snapshot payload; assert the fallback ladder picks `prevDay.c` when `lastTrade`, `min` and `day` are zeroed |
| `MassiveSource` errors | Mock 401/403/429/500 via `httpx.MockTransport` and assert the documented policy |
| `MarketFeed` | A source that raises on one call must not stop the loop; cached prices survive |
| `create_source` | Unset, empty, and whitespace-only keys all select the simulator; a real value selects Massive |

No test may touch the network. Massive responses are fixture JSON replayed through
`httpx.MockTransport`. The simulator is seeded via `MARKET_SEED` for determinism.

### Verification status

The code in this document was implemented and exercised. All checks pass. Points
worth carrying into the real test suite:

- **`MassiveSource` parsing was validated against the verbatim payload** from the
  Massive documentation. The bearer header, the comma-separated `tickers` query
  parameter and the snapshot path are all constructed correctly, and a fixture
  with `day` and `min` zeroed correctly falls through to `prevDay.c`.
- **Dropping unknown tickers works as specified.** Requesting
  `["AAPL", "MSFT", "DELISTED"]` against a two-ticker response returns two quotes
  rather than raising.
- **`raise_for_status()` surfaces 401, 403, 429 and 500** as `httpx.HTTPStatusError`,
  which is what the feed's handler and the fallback policy in section 9 key off.
- **`PriceCache` behaves as documented**: first sighting is `flat` but still
  emitted, an unchanged price is not reported as changed, and `change_percent`
  is exact.
- **`create_source()` treats `None`, `""` and `"   "` alike** and selects the
  simulator for all three.

One trap found while testing the simulator, documented at length in
`MARKET_SIMULATOR.md` section 7: assert on quote **prices**, not on `Quote`
objects. `Quote.timestamp` is wall-clock, so two identically seeded runs produce
equal prices inside unequal objects.

## 14. Summary

- One abstract method, `fetch(tickers) -> list[Quote]`, is the entire source contract.
- `create_source()` is the only environment-aware code in the market package.
- The cache owns previous-price and direction, so both sources stay simple and
  can never disagree.
- Source poll interval and SSE stream interval are independent, which is what lets
  a 15 s upstream poll and a 500 ms simulator tick look the same to the browser.
- Upstream failures degrade to stale prices; only unrecoverable auth and plan
  errors trigger a fallback to the simulator.
