# Market Data Design

A single, implementation-ready design for FinAlly's market data backend: one
unified Python interface with two implementations — a built-in simulator
(default) and a Massive (formerly Polygon.io) REST client (when
`MASSIVE_API_KEY` is set) — feeding an in-memory cache that the SSE stream,
portfolio valuation, and trade execution all read from.

This document consolidates and supersedes the three companion research
documents (`MARKET_INTERFACE.md`, `MARKET_SIMULATOR.md`, `MASSIVE_API.md`) into
a single build reference. Consult those for the underlying derivations and
verification evidence; everything needed to implement the module lives here.

> Note: `planning/archive/MARKET_DATA_DESIGN.md` is a superseded draft. Do not
> use it as a reference — this document replaces it.

## 1. Overview

Per `PLAN.md` section 6, the backend streams live prices to the frontend over
SSE. The source of those prices is environment-driven:

- No `MASSIVE_API_KEY` → an in-process GBM simulator generates believable,
  correlated, always-positive price action at 2 Hz. No network, no
  dependencies, works everywhere. This is the default and primary demo
  experience.
- `MASSIVE_API_KEY` set → a REST poller pulls real snapshot data from Massive
  every 15 seconds (configurable).

Both are hidden behind one abstract interface so that the cache, the feed
loop, the SSE endpoint, and the frontend never know or care which is active.

### Design goals

1. **One seam.** Exactly one function (`create_source()`) decides which data
   source is live. Nothing else in the codebase branches on the environment
   variable.
2. **Source cadence is not stream cadence.** The simulator ticks every 500 ms;
   the Massive poller runs every 15 s. The SSE stream looks identical either
   way because it reads a cache, not a source.
3. **Pull, not push.** A source exposes a plain `fetch(tickers)` coroutine. A
   separate background feed owns timing. No callbacks, no observer
   registration.
4. **Sources do not hold history.** A source answers "what is the price now."
   The cache is the only component that remembers a previous price and
   derives direction — so the two sources can never disagree about "did it go
   up."
5. **Degrade, do not crash.** An upstream failure serves stale cached prices;
   it never takes down the app.

## 2. Architecture & Module Layout

```
backend/app/market/
├── __init__.py       # public exports
├── models.py         # Quote, PriceUpdate
├── interface.py       # MarketDataSource abstract base class
├── simulator.py       # SimulatorSource
├── seed_prices.py     # anchor prices / profiles for the simulator
├── massive.py          # MassiveSource
├── cache.py           # PriceCache
├── feed.py            # MarketFeed background task
└── factory.py         # create_source()
```

Dependency direction is strictly one way:

```
factory ──> simulator ──┐
        └─> massive ────┴──> interface ──> models
                                              ^
feed ──> cache ───────────────────────────────┘
```

`cache.py` and `feed.py` never import a concrete source. `simulator.py` and
`massive.py` never import each other. Application code depends only on
`MarketDataSource`, obtained through `create_source()` — concrete source
classes are not part of the public API (see section 11).

```
MarketDataSource (ABC)
├── SimulatorSource   →  GBM simulator (default, no API key needed)
└── MassiveSource     →  Massive REST poller (when MASSIVE_API_KEY set)
        │
        ▼
   PriceCache (single-writer, in-memory)
        │
        ├──→ SSE stream endpoint (/api/stream/prices)
        ├──→ Portfolio valuation
        └──→ Trade execution
```

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

**Why two models.** A source reports a single observation and has no business
knowing what came before. Keeping `previous_price` out of `Quote` means the
simulator does not have to track it, the Massive client does not have to
track it, and there is exactly one implementation of "did it go up" — in the
cache. If both sources computed direction independently, they would
eventually disagree.

## 4. The Unified Interface

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
- `fetch` is **stateless with respect to the caller** — calling it twice with
  the same tickers is always valid.
- `fetch` **may return fewer quotes than requested**. Unknown, delisted, or
  temporarily unavailable tickers are dropped silently. Callers must not
  assume a one-to-one mapping.
- `fetch` **raises only on total failure** (network down, auth rejected). A
  partial result is a success.
- `poll_interval` is advisory and read once by the feed when it starts.

This one abstract method is the entire seam between "where prices come from"
and everything downstream.

## 5. The Market Simulator

The default data source. It generates believable price action with no API
key, no network access, and no external dependencies.

### 5.1 Requirements

- Prices move continuously and look plausible on a chart
- Updates every 500 ms so the UI flashes green/red constantly
- Related tickers move together (tech stocks correlate, defensives lag)
- Occasional sudden 2–5% moves for drama
- Never zero or negative
- Stays in a believable range even after days of continuous running
- Reproducible under a fixed seed for deterministic tests
- Prices any ticker the user invents, not just the default ten

### 5.2 The model

Prices follow **geometric Brownian motion (GBM)**, discretised per tick:

```
S(t+dt) = S(t) * exp( drift * dt + sigma * sqrt(dt) * Z ),   Z ~ N(0, 1)
```

GBM is the right choice for one structural reason: because the price is
multiplied by `exp(...)`, and `exp` is strictly positive, **the price can
never reach zero or go negative**. No clamping, no `max(price, 0.01)` guard —
positivity is a property of the model, not a defensive check. It also means
returns compound proportionally, so an $880 NVDA and a $175 GOOGL both move by
sensible *percentages* rather than the same dollar amount.

**Time step.** `dt` is measured in *trading* years so the volatility
parameter is the familiar annualised figure:

```
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600 = 5,896,800
DT = 0.5 / 5,896,800 = 8.479e-8
```

Using trading time (252 days × 6.5 hours) rather than wall-clock time (365
days × 24 hours) is what makes a configured volatility of 0.28 actually mean
"28% annualised."

**Anchor pull instead of drift.** Plain GBM with positive drift wanders
without bound — over a long-running container this produces absurd prices,
made worse by the random events compounding as a random walk (90 events of
~3.5% each compound to roughly `3.5% * sqrt(90) ≈ 33%` of cumulative drift).
Measured with no anchor pull: a single 6.5-hour session moved prices 7.2% on
average with a 14.2% range, and it only gets worse over days.

So the drift term is replaced by a logarithmic pull back toward an anchor
price — an Ornstein-Uhlenbeck process in log space:

```
pull = KAPPA * ln(anchor / S) * dt
```

When price sits above its anchor, pull is negative; below it, pull is
positive. Strength is proportional to how far the price has strayed, so it's
invisible in normal trading and only asserts itself after a large move.
`KAPPA = 175` gives a half-life of roughly one trading session
(`ln(2) * 252 ≈ 175`); verified over 5 continuous simulated days, maximum
deviation from anchor stayed within 14% (vs. unbounded growth without it).
This also removes a per-ticker drift knob — the anchor pull *is* the drift.

**The complete step:**

```
Z_market      ~ N(0, 1)                       shared by all tickers this tick
Z_i           = beta_i * Z_market + sqrt(1 - beta_i^2) * N(0, 1)
pull          = KAPPA * ln(anchor_i / S_i) * DT
ito           = -0.5 * sigma_i^2 * DT
shock         = sigma_i * sqrt(DT) * Z_i

S_i(t+dt)     = S_i(t) * exp(pull + ito + shock)
```

The `ito` term is the standard Itô correction, keeping the *expected* price
centred on the anchor rather than drifting upward by `sigma^2/2` (a log-normal
artefact). Its practical effect is tiny (~0.02% for AAPL) but it's one term
and makes the model correct.

**Correlation via one market factor.** `Z_market` is drawn once per tick and
shared; each ticker mixes it with its own independent noise via
`beta_i`. Two properties make this work:

1. `Var(Z_i) = beta^2 + (1 - beta^2) = 1` — unit variance is preserved, so
   `beta` changes correlation **without** changing volatility. The two knobs
   stay independent.
2. `corr(Z_i, Z_j) = beta_i * beta_j` — two tech names at `beta = 0.85`
   correlate at 0.72; tech against JPM at `beta = 0.50` correlates at 0.43.

The result: a watchlist that mostly moves as a bloc, with defensive names
lagging — what a real market looks like.

*Rejected alternative:* a full correlation matrix with Cholesky decomposition.
It allows arbitrary pairwise correlations but requires a positive
semi-definite matrix that must be hand-tuned and re-validated whenever a
ticker is added, plus a matrix library. The one-factor model needs a single
number per ticker and cannot be made inconsistent.

**Drama events.** Each ticker, each tick, with probability `EVENT_PROB = 8e-5`
takes an extra jump of 2–5% in a random direction (roughly one event every ten
minutes across a 10-ticker watchlist — often enough a user watching for a few
minutes will probably see one). A jump multiplies by `1 ± magnitude` with
magnitude at most 0.05, so it can't produce a negative price either.

This deliberately exaggerates intraday range: measured mean range across the
watchlist is 9.33% at the chosen rate vs. 3.35% for diffusion alone (real
large-caps typically range 1.5–3%). `PLAN.md` explicitly asks for these events
"for drama," so demo value wins over realism here. If a deployment runs all
day and this becomes distracting, `EVENT_PROBABILITY = 2e-5` is the
realism-leaning setting. **Events must be disabled (`EVENT_PROBABILITY = 0`)
when testing volatility/correlation statistics** — jumps are large and
idiosyncratic enough to swamp the diffusion (they moved measured AAPL
volatility from 0.28 to 1.25 and correlation from 0.72 to 0.05 in testing).

### 5.3 Ticker profiles

`seed_prices.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TickerProfile:
    """Static characteristics of a simulated ticker."""

    anchor: float
    """Price the random walk is pulled back toward."""

    volatility: float
    """Annualised volatility, e.g. 0.28 for 28%."""

    beta: float
    """Correlation with the shared market factor, 0 to 1."""


PROFILES: dict[str, TickerProfile] = {
    "AAPL":  TickerProfile(190.0, 0.28, 0.85),
    "GOOGL": TickerProfile(175.0, 0.32, 0.85),
    "MSFT":  TickerProfile(420.0, 0.26, 0.85),
    "AMZN":  TickerProfile(185.0, 0.35, 0.80),
    "TSLA":  TickerProfile(250.0, 0.60, 0.70),
    "NVDA":  TickerProfile(880.0, 0.55, 0.75),
    "META":  TickerProfile(500.0, 0.38, 0.80),
    "JPM":   TickerProfile(200.0, 0.22, 0.50),
    "V":     TickerProfile(280.0, 0.20, 0.55),
    "NFLX":  TickerProfile(610.0, 0.40, 0.65),
}

DEFAULT_VOLATILITY = 0.35
DEFAULT_BETA = 0.70
```

The ten defaults match the seed watchlist in `PLAN.md` section 7. Anchors are
realistic round numbers; volatilities and betas reflect each name's
character — TSLA and NVDA are the volatile high-beta movers, JPM and V the
steadier low-beta ones. These are demo parameters, not a market forecast.

**Unknown tickers.** The user can add any symbol, so the simulator must price
symbols it has never seen. It derives a stable profile from the ticker string
itself:

```python
import hashlib


def profile_for(ticker: str) -> TickerProfile:
    """Profile for a known ticker, or a deterministic synthetic one."""
    if ticker in PROFILES:
        return PROFILES[ticker]

    digest = hashlib.md5(ticker.encode()).hexdigest()
    anchor = 20.0 + (int(digest[:8], 16) % 38000) / 100.0
    return TickerProfile(anchor, DEFAULT_VOLATILITY, DEFAULT_BETA)
```

This yields an anchor between $20.00 and $399.99. **Use `hashlib`, not the
built-in `hash()`** — Python salts `hash()` for strings with a per-process
random seed unless `PYTHONHASHSEED` is fixed, so the built-in would give a
ticker a different price after every container restart. `hashlib.md5` is
stable across processes and machines; it's used only as a stable
string-to-number map, not as a security primitive. Verified sample: PYPL
$100.29, AMD $275.69, BRK.B $227.73 — same values on every run.

### 5.4 Implementation

`simulator.py`

```python
import math
import os
import random
from collections.abc import Sequence
from datetime import UTC, datetime

from .interface import MarketDataSource
from .models import Quote
from .seed_prices import profile_for

TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
TICK_SECONDS = 0.5
DT = TICK_SECONDS / TRADING_SECONDS_PER_YEAR

KAPPA = 175.0
"""Anchor pull strength. ln(2) * 252 gives a one-session half-life."""

EVENT_PROBABILITY = 8e-5
EVENT_MIN, EVENT_MAX = 0.02, 0.05


class SimulatorSource(MarketDataSource):
    """Geometric Brownian motion price simulator."""

    name = "simulator"
    poll_interval = TICK_SECONDS

    def __init__(self, seed: int | None = None) -> None:
        if seed is None:
            env_seed = os.getenv("MARKET_SEED")
            seed = int(env_seed) if env_seed else None
        self._rng = random.Random(seed)
        self._prices: dict[str, float] = {}

    async def fetch(self, tickers: Sequence[str]) -> list[Quote]:
        """Advance every requested ticker one tick."""
        market_shock = self._rng.gauss(0, 1)
        now = datetime.now(UTC)
        return [
            Quote(ticker, self._advance(ticker, market_shock), now)
            for ticker in tickers
        ]

    def _advance(self, ticker: str, market_shock: float) -> float:
        profile = profile_for(ticker)
        price = self._prices.get(ticker, profile.anchor)
        sigma = profile.volatility

        shock = profile.beta * market_shock + math.sqrt(
            1 - profile.beta**2
        ) * self._rng.gauss(0, 1)

        pull = KAPPA * math.log(profile.anchor / price) * DT
        ito = -0.5 * sigma**2 * DT
        diffusion = sigma * math.sqrt(DT) * shock

        price *= math.exp(pull + ito + diffusion)
        price *= self._event_multiplier()

        self._prices[ticker] = price
        return round(price, 2)

    def _event_multiplier(self) -> float:
        """Occasional 2-5% jump for drama. Returns 1.0 most ticks."""
        if self._rng.random() >= EVENT_PROBABILITY:
            return 1.0
        magnitude = self._rng.uniform(EVENT_MIN, EVENT_MAX)
        return 1 + magnitude if self._rng.random() < 0.5 else 1 - magnitude
```

About 50 lines, standard library only. Key implementation notes:

- **Full precision is stored, rounding happens at the boundary.**
  `self._prices` holds the unrounded float; only the returned `Quote` is
  rounded to cents. Rounding the stored value would quantise the walk onto a
  one-cent lattice and inject bias that compounds over tens of thousands of
  ticks.
- **One market shock per `fetch`, not per ticker.** Drawing `market_shock`
  once in `fetch` and passing it into each `_advance` call is what creates the
  correlation. Drawing it inside `_advance` would make every ticker
  independent and silently destroy the feature.
- **No numpy.** `random.gauss` is sufficient for ten tickers at 2 Hz and keeps
  the dependency out of the Docker image. Only worth vectorising if the
  watchlist grows to thousands of tickers.
- **Lazy initialisation.** A ticker enters `self._prices` the first time it's
  requested, starting at its anchor. Adding a ticker to the watchlist
  mid-session needs no special handling.
- **Ignores market hours.** Runs at full speed at 3 AM on a Sunday —
  deliberate, since a frozen screen outside market hours is a broken-looking
  demo.

### 5.5 Verified behaviour

Per-tick moves (1-sigma):

| Horizon | Steadiest (V, σ 0.20) | Most volatile (TSLA, σ 0.60) |
|---|---|---|
| One tick (500 ms) | 0.006% ($0.016) | 0.017% ($0.044) |
| One minute | 0.064% | 0.191% |
| One hour | 0.49% | 1.48% |
| Full session | 1.26% | 3.78% |

Every ticker's rounded price changes on at least 70% of ticks over a full
session (NVDA 97.2% down to JPM 70.3%), so the watchlist is in near-constant
motion at 2 Hz while the underlying percentage moves stay realistic.

Parameter sweep that produced `KAPPA = 175`, `EVENT_PROBABILITY = 8e-5` (8
seeds × 46,800-tick sessions):

| KAPPA | EVENT_PROBABILITY | mean abs change | mean range | events |
|---|---|---|---|---|
| 0 | 2e-4 | 7.16% | 14.23% | 87 |
| 0 | 8e-5 | 5.85% | 10.26% | 40 |
| 175 | 2e-4 | 5.46% | 13.39% | 87 |
| **175** | **8e-5** | **4.25%** | **9.44%** | **37** |
| 500 | 8e-5 | 2.74% | 8.78% | 40 |

`KAPPA = 500` was rejected as visibly over-damped — prices rubber-band to the
anchor and stop looking like a market.

### 5.6 Configuration

| Variable | Default | Effect |
|---|---|---|
| `MARKET_SEED` | unset | Fixes the RNG seed. Set in tests for reproducibility; leave unset in production so each run differs. |

`KAPPA`, `EVENT_PROBABILITY`, and `DT` are module-level constants, not
environment variables — they are validated tuning decisions, not deployment
settings.

## 6. The Massive Source

Real market data, used when `MASSIVE_API_KEY` is set. Massive is the rebrand
(30 October 2025) of Polygon.io; existing keys and API paths are unchanged.

### 6.1 Plans and rate limits — the deciding fact

| Plan | Price | Requests/min | Data freshness | Snapshot endpoints |
|---|---|---|---|---|
| Stocks Basic | Free | 5 | End of day | **Not included** |
| Stocks Starter | $29/mo | Unlimited | 15-minute delayed | Included |
| Stocks Developer | $79/mo | Unlimited | 15-minute delayed | Included |
| Stocks Advanced | $199/mo | Unlimited | Real-time | Included |

**A free Stocks Basic key cannot call the snapshot endpoint at all — it
returns 403, and the plan is end-of-day only regardless.** There is no
configuration that makes a free key stream live prices. The simulator remains
the default experience for exactly this reason, matching `PLAN.md`.

### 6.2 The endpoint

**Full Market Snapshot** — one request returns every watchlist ticker, so a
10-ticker watchlist costs one call, not ten:

```
GET /v2/snapshot/locale/us/markets/stocks/tickers
```

| Parameter | Type | Notes |
|---|---|---|
| `tickers` | string | Case-sensitive comma-separated list, e.g. `AAPL,TSLA,GOOG` |
| `include_otc` | boolean | Default `false` |

Requires Stocks Starter or higher. Response shape:

```json
{
  "status": "OK",
  "count": 1,
  "tickers": [
    {
      "ticker": "AAPL",
      "todaysChange": 0.98,
      "todaysChangePerc": 0.82,
      "updated": 1605195918306274000,
      "day":     { "o": 119.62, "h": 120.53, "l": 118.81, "c": 120.4229, "v": 28727868, "vw": 119.725 },
      "prevDay": { "o": 117.19, "h": 119.63, "l": 116.44, "c": 119.49,   "v": 110597265, "vw": 118.4998 },
      "min":     { "o": 120.435, "h": 120.468, "l": 120.37, "c": 120.4201, "v": 270796, "av": 28724441, "vw": 120.4129, "n": 762, "t": 1684428720000 },
      "lastTrade": { "p": 120.47, "s": 236, "t": 1605195918306274000, "x": 10, "i": "4046", "c": [14, 41] },
      "lastQuote": { "p": 120.46, "s": 8, "P": 120.47, "S": 4, "t": 1605195918507251700 }
    }
  ]
}
```

**The zero-value gotcha.** Snapshot data clears daily at 3:30 AM ET and only
repopulates as exchanges report, starting as early as 4:00 AM ET. Between
those times, and on weekends/holidays, `day.c` and `min.c` are `0`. Never read
`day.c` blindly — use a fallback ladder:

```python
price = (
    snap.get("lastTrade", {}).get("p")
    or snap.get("min", {}).get("c")
    or snap.get("day", {}).get("c")
    or snap.get("prevDay", {}).get("c")
)
```

`prevDay.c` is the only field reliably non-zero around the clock.

**Timestamp units are inconsistent** — `lastTrade.t`, `lastQuote.t`, and
`updated` are nanoseconds; `min.t` is milliseconds. Not needed for our use
case (we stamp our own `datetime.now(UTC)`), but a trap if this data is ever
consumed elsewhere.

*(v3 `/v3/snapshot?ticker.any_of=...` exists as a flatter, multi-asset
alternative accepting up to 250 tickers, but for a stocks-only watchlist it
offers no practical advantage over v2 and adds pagination handling — not
used.)*

### 6.3 Authentication

```
Authorization: Bearer <MASSIVE_API_KEY>
```

Prefer the header over the `?apiKey=` query-parameter form, which leaks the
key into access logs, proxy logs, and browser history. `MASSIVE_API_KEY` is
the same variable name `PLAN.md` already specifies — no mapping needed.

### 6.4 Implementation

**Why raw `httpx` and not the official `massive` client:** the official
package (v2.8.0, `from massive import RESTClient`) is built on
`urllib3.PoolManager` and is **synchronous**. Calling it from a FastAPI
coroutine blocks the event loop and stalls every open SSE connection, so every
call would need `asyncio.to_thread` offloading. We need exactly one endpoint —
a direct `httpx` call is natively async, has no hidden retry behaviour, and is
less code than the offload wrapper.

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

Unknown or delisted tickers are simply absent from `payload["tickers"]`; the
walrus-guarded comprehension drops them without raising, matching the
interface contract in section 4.

### 6.5 Error handling

| Status | Meaning | Response |
|---|---|---|
| 200, `"status": "OK"` | Success | Normal path |
| 401 | Missing/invalid key | Permanent — log clearly, fall back to `SimulatorSource` |
| 403 | Key valid, plan excludes the endpoint | Permanent — expected on a free key; fall back to `SimulatorSource` |
| 429 | Rate limit exceeded | Transient — back off by doubling the poll interval up to a 60 s ceiling |
| 5xx, timeouts, network errors | Upstream fault | Transient — log and retry next tick, serving cached prices |

A 200 response can still carry `"status": "NOT_AUTHORIZED"` or `"ERROR"` in
the body, so the `status` field is worth checking in addition to the HTTP
code if this is extended later.

**Why auto-fallback on 401/403 is worth the trade-off:** it hides a
misconfiguration, which is normally bad, but a wrong key on a course project
would otherwise yield a blank, priceless UI with no explanation. The loud log
line is what keeps this honest, and it only triggers on errors that will
never self-heal. This policy is implemented in the feed/factory layer (section
8–9), not inside `MassiveSource` itself — the source's job is only to raise
`httpx.HTTPStatusError` via `raise_for_status()`.

### 6.6 If real historical/backtest data is needed later

Not part of the live-price feed, but useful references documented in
`MASSIVE_API.md`:

- Free-tier daily bars for all tickers in one call:
  `GET /v2/aggs/grouped/locale/us/market/stocks/{date}` (available on Basic)
- Previous day bar for one ticker (auto weekend/holiday walk-back):
  `GET /v2/aggs/ticker/{ticker}/prev`
- Custom historical bars (for future chart history):
  `GET /v2/aggs/ticker/{ticker}/range/{mult}/{timespan}/{from}/{to}`

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
`direction` is `"flat"` and the frontend does not flash a spurious colour on
page load — but that first update is still emitted, so the client learns the
price immediately.

No lock is needed: a single feed task is the only writer, and asyncio gives it
uncontended access between awaits. The cache is deliberately not persisted —
prices are ephemeral, and restarting the container starts from fresh quotes.

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

`tickers` is a callable, not a list, so the feed picks up watchlist additions
on the next poll without knowing anything about the database.

The broad `except Exception` here is deliberate and is the one place
defensive handling earns its place: a transient upstream failure must not
kill the only task feeding the entire application. Everything else keeps
working off cached prices.

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

`.strip()` matters: `.env` files routinely contain `MASSIVE_API_KEY=` or a
value with trailing whitespace, and a whitespace-only key must count as
absent.

### Environment variables

| Variable | Default | Effect |
|---|---|---|
| `MASSIVE_API_KEY` | unset | Non-empty selects `MassiveSource`; empty, unset, or whitespace-only selects `SimulatorSource` |
| `MARKET_POLL_INTERVAL` | `15` | Massive poll interval in seconds. Ignored by the simulator. |
| `MARKET_SEED` | unset | Fixes the simulator's RNG seed for reproducible tests |

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
`request.app.state.prices`. `watchlist_tickers` is a callable supplied by the
portfolio/watchlist module that reads the current watchlist from SQLite (or an
in-memory cache of it) — the market package never queries the database
directly.

### SSE streaming: `/api/stream/prices`

This is where source cadence is decoupled from stream cadence. The endpoint
reads the cache on its own fixed 500 ms schedule and never touches the
source:

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

Each new subscriber receives a full snapshot immediately, so a page load
renders prices without waiting for the next poll. After that, only changed
tickers are sent — with a 15 s Massive poll, 96% of naive per-tick frames
would otherwise be byte-identical repeats. The observable behaviour for the
frontend is unchanged either way, because a repeated price produces a `flat`
direction and no flash. A comment heartbeat every 15 s should be added to keep
idle connections and intermediate proxies alive.

```python
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("/api/stream/prices")
async def stream_prices(request: Request):
    cache = request.app.state.prices
    return EventSourceResponse(price_events(cache))


def _format(update) -> dict:
    return {
        "event": "price",
        "data": {
            "ticker": update.ticker,
            "price": update.price,
            "previous_price": update.previous_price,
            "change": update.change,
            "change_percent": round(update.change_percent, 4),
            "direction": update.direction,
            "timestamp": update.timestamp.isoformat(),
        },
    }
```

## 11. Public Exports

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

Concrete sources (`SimulatorSource`, `MassiveSource`) are intentionally not
exported. Application code obtains a source through `create_source()` and
depends only on the abstract `MarketDataSource` type — this is what keeps the
environment-variable branch confined to one function.

## 12. Testing Strategy

No test may touch the network. Massive responses are fixture JSON replayed
through `httpx.MockTransport`. The simulator is seeded via `MARKET_SEED` (or
the constructor's `seed` argument) for determinism.

| Target | Test |
|---|---|
| Interface conformance | Parametrise one test over both sources: `fetch` returns `Quote` objects, never raises on an empty ticker list, tolerates unknown symbols |
| `PriceCache` | First sighting yields `flat`; a rise yields `up`; an unchanged price is not reported as changed; `change_percent` maths |
| `SimulatorSource` determinism | Two instances with the same seed produce identical **price** sequences over N ticks |
| `SimulatorSource` statistics | Realised volatility within 5% of configured `sigma`; correlation ordering (`corr(AAPL, MSFT) > corr(AAPL, JPM)`) with `EVENT_PROBABILITY = 0` |
| `SimulatorSource` positivity | Over 100k quotes, every price is `> 0` |
| `SimulatorSource` unknown tickers | `profile_for("PYPL")` is stable across processes with differing `PYTHONHASHSEED` |
| `MassiveSource` parsing | Parse a captured snapshot payload; assert the fallback ladder picks `prevDay.c` when `lastTrade`, `min`, and `day` are zeroed |
| `MassiveSource` errors | Mock 401/403/429/500 via `httpx.MockTransport` and assert the documented policy |
| `MarketFeed` resilience | A source that raises on one call must not stop the loop; cached prices survive |
| `create_source` | Unset, empty, and whitespace-only keys all select the simulator; a real value selects Massive |

Two traps worth calling out explicitly:

- **Compare prices, not `Quote` objects.** `Quote.timestamp` is wall-clock
  `datetime.now(UTC)`, so two identically seeded runs produce equal prices
  inside unequal objects. Asserting `run_a == run_b` on the quotes fails for a
  reason unrelated to the model.
- **Disable events (`EVENT_PROBABILITY = 0.0`) before measuring volatility or
  correlation.** With events enabled at the default rate, a 10,000-tick
  sample of AAPL measures volatility of 1.25 against a configured 0.28, and
  correlation collapses from 0.72 to 0.05 — the jumps are large, idiosyncratic,
  and swamp the diffusion. This is the model behaving correctly, not a defect,
  but it makes the parameters untestable unless jumps are switched off for
  that specific test.

## 13. Summary

- One abstract method, `fetch(tickers) -> list[Quote]`, is the entire market
  data source contract (`interface.py`).
- `create_source()` is the only environment-aware code in the market package —
  it reads `MASSIVE_API_KEY` and returns either `SimulatorSource` or
  `MassiveSource`, both behind the same abstract type.
- The **simulator** (`simulator.py` + `seed_prices.py`) is ~50 lines of
  standard-library GBM: anchor-pull replaces drift to bound long-run
  wandering, a single shared market factor produces realistic cross-ticker
  correlation, and rare 2–5% jumps deliver demo drama. Positivity is
  guaranteed by the model's structure, not by clamping.
- The **Massive source** (`massive.py`) calls the v2 full-market-snapshot
  endpoint with raw `httpx` (the official client is synchronous and would
  block the event loop), authenticates via bearer header, and falls through
  `lastTrade → min → day → prevDay` to dodge the nightly zero-value window. A
  free-tier key cannot use it at all, which is why the simulator stays the
  default.
- The **cache** (`cache.py`) owns previous-price and direction, so both
  sources stay simple and can never disagree.
- The **feed** (`feed.py`) decouples source poll interval from SSE stream
  interval — a 15 s upstream poll and a 500 ms simulator tick look identical
  to the browser — and never lets a transient upstream failure take down the
  app.
- Upstream failures degrade to stale cached prices; only unrecoverable auth
  and plan errors (401/403) trigger a logged fallback to the simulator.
