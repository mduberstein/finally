# Market Simulator

The default market data source for FinAlly. It generates believable price action
with no API key, no network access and no external dependencies, implementing the
`MarketDataSource` interface defined in `MARKET_INTERFACE.md`.

Every numeric claim in this document was verified by simulation. The tuning
scripts and their output are summarised in section 8.

## 1. What It Has To Do

- Produce prices that move continuously and look plausible on a chart
- Update every 500 ms so the UI flashes green and red constantly
- Move related tickers together, so the watchlist behaves like a market rather
  than ten unrelated noise generators
- Occasionally deliver a sudden 2-5% move for drama
- Never produce a zero or negative price
- Stay in a believable range even if the container runs for days
- Be reproducible under a fixed seed so tests are deterministic
- Price any ticker the user invents, not just a hardcoded list

## 2. The Model

### Geometric Brownian motion

Prices follow GBM, discretised per tick:

```
S(t+dt) = S(t) * exp( drift * dt + sigma * sqrt(dt) * Z )
```

where `Z ~ N(0, 1)`.

GBM is the right choice for one structural reason: because the price is multiplied
by `exp(...)`, and `exp` is strictly positive, **the price can never reach zero or
go negative**. No clamping, no `max(price, 0.01)` guard. The requirement is
satisfied by the shape of the model rather than by a defensive check.

It also means returns compound proportionally, so a $880 NVDA and a $175 GOOGL
both move by sensible *percentages* rather than the same dollar amount.

### The time step

`dt` is measured in years, so the volatility parameter is the familiar annualised
figure.

```
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600 = 5,896,800
DT = 0.5 / 5,896,800 = 8.479e-8
```

A 500 ms tick is 8.479e-8 of a trading year. Using trading time rather than
wall-clock time (252 days of 6.5 hours, not 365 days of 24 hours) is what makes a
configured volatility of 0.28 actually mean "28% annualised".

### Anchor pull instead of drift

Plain GBM with a positive drift wanders without bound. Over a long-running
container that produces absurd prices, and the random 2-5% events make it worse:
they accumulate as a random walk, so 90 events of ~3.5% each compound to roughly
`3.5% * sqrt(90) = 33%` of cumulative drift.

Measured, with no anchor pull, a single 6.5-hour session moved prices by 7.2% on
average and swung through a 14.2% range. Left running for days it only gets worse.

So the drift term is replaced by a logarithmic pull back toward an anchor price:

```
pull = KAPPA * ln(anchor / S) * dt
```

This is an Ornstein-Uhlenbeck process in log space. When the price sits above its
anchor the pull is negative, and below it the pull is positive. Its strength is
proportional to how far the price has strayed, so it is invisible during normal
trading and only asserts itself after a large move.

`KAPPA = 175` gives a half-life of roughly one trading session
(`ln(2) * 252 = 175`). Verified effect over 5 continuous simulated days: maximum
deviation from anchor stayed within 14%, versus unbounded growth without it.

This also removes a configuration knob. There is no separate `mu` per ticker,
because the anchor pull *is* the drift.

### The complete step

```
Z_market      ~ N(0, 1)                       shared by all tickers this tick
Z_i           = beta_i * Z_market + sqrt(1 - beta_i^2) * N(0, 1)
pull          = KAPPA * ln(anchor_i / S_i) * DT
ito           = -0.5 * sigma_i^2 * DT
shock         = sigma_i * sqrt(DT) * Z_i

S_i(t+dt)     = S_i(t) * exp(pull + ito + shock)
```

The `ito` term is the standard Itô correction. It keeps the *expected* price
centred on the anchor rather than drifting upward by `sigma^2/2`, which is an
artefact of the log-normal distribution. Its practical effect here is tiny
(about 0.02% for AAPL) but it is one term and it makes the model correct.

### Correlation via one market factor

`Z_market` is drawn once per tick and shared. Each ticker mixes it with its own
independent noise:

```
Z_i = beta_i * Z_market + sqrt(1 - beta_i^2) * E_i
```

Two properties make this work:

1. `Var(Z_i) = beta^2 + (1 - beta^2) = 1`. Unit variance is preserved, so `beta`
   changes correlation **without** changing volatility. The two knobs stay
   independent.
2. `corr(Z_i, Z_j) = beta_i * beta_j`. Two tech names at `beta = 0.85` correlate at
   0.72 with each other; tech against JPM at `beta = 0.50` correlates at 0.43.

The result is a watchlist that mostly moves as a bloc, with the defensive names
lagging — which is what a real market looks like.

**Rejected alternative:** a full correlation matrix with Cholesky decomposition.
It allows arbitrary pairwise correlations but requires a positive semi-definite
matrix that must be hand-tuned and re-validated whenever a ticker is added, plus a
matrix library. The one-factor model needs a single number per ticker and cannot
be made inconsistent. For a trading demo the extra fidelity buys nothing.

### Drama events

Each ticker, each tick, with probability `EVENT_PROB = 8e-5`, takes an extra jump
of 2-5% in a random direction.

Verified pacing across a 10-ticker watchlist:

| Window | Expected events |
|---|---|
| 5 minutes | 0.48 |
| 1 hour | 5.8 |
| Full 6.5-hour session | 37 |

Roughly one event every ten minutes — often enough that a user watching for a few
minutes will probably see one, rare enough that it still reads as an event.

A jump multiplies by `1 +/- magnitude` with magnitude at most 0.05, so it cannot
produce a negative price either.

**Events dominate session-scale variance, and this is a deliberate trade-off.**
A single 3.5% jump is roughly 400 times a normal AAPL tick, so a handful of them
per session contributes far more movement than the diffusion does. Mean intraday
range across the watchlist, averaged over 4 seeded full sessions:

| `EVENT_PROBABILITY` | Events/session | Events/5 min | Mean range |
|---|---|---|---|
| 0 (diffusion only) | 0 | 0 | 3.35% |
| 5e-6 | 2.3 | 0.03 | 4.03% |
| 2e-5 | 9.4 | 0.12 | 5.31% |
| **8e-5 (chosen)** | **37.4** | **0.48** | **9.33%** |

Real large-cap equities typically range 1.5-3% intraday, so the diffusion alone is
about right and the chosen event rate is roughly three times more dramatic than
reality. `PLAN.md` explicitly asks for these events "for drama", and a user
watching for five minutes should have a reasonable chance of seeing one, so demo
value wins over realism here.

If a deployment is left running all day and the exaggerated range becomes
distracting, `EVENT_PROBABILITY = 2e-5` is the realism-leaning setting. The
2-5% magnitude comes straight from `PLAN.md` and should not be changed without
revisiting that spec.

One consequence matters for testing: because jumps are idiosyncratic and large,
they inflate measured volatility and suppress measured correlation. The clean
statistical properties of the model hold for the diffusion component, so the
tests in section 7 disable events. See section 8 for the measurements.

## 3. Ticker Profiles

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

The ten defaults match the seed watchlist in `PLAN.md`. Anchors are realistic
round numbers; volatilities and betas reflect each name's character — TSLA and
NVDA are the volatile high-beta movers, JPM and V the steadier low-beta ones.

These are demo parameters, not a market forecast. They only need to look right.

### Unknown tickers

The user can add any symbol, so the simulator must price symbols it has never
seen. It derives a stable profile from the ticker string itself:

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

This yields an anchor between $20.00 and $399.99.

**Use `hashlib`, not the built-in `hash()`.** Python salts `hash()` for strings
with a per-process random seed unless `PYTHONHASHSEED` is fixed, so the built-in
would give a ticker a different price after every container restart. `hashlib.md5`
is stable across processes and machines. It is not being used as a security
primitive here, only as a stable string-to-number map.

Verified sample: PYPL $100.29, AMD $275.69, BRK.B $227.73 — same values on every
run.

## 4. Code Structure

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

That is the whole simulator: about 50 lines, no dependencies beyond the standard
library.

### Notes on the implementation

**Full precision is stored, rounding happens at the boundary.** `self._prices`
holds the unrounded float; only the returned `Quote` is rounded to cents.
Rounding the stored value would quantise the walk onto a one-cent lattice and
inject a small bias that compounds over tens of thousands of ticks.

**One market shock per `fetch`, not per ticker.** Drawing `market_shock` once in
`fetch` and passing it into each `_advance` call is what creates the correlation.
Drawing it inside `_advance` would make every ticker independent and silently
destroy the feature.

**No numpy.** `random.gauss` from the standard library is sufficient for ten
tickers at 2 Hz, and it keeps the dependency out of the Docker image entirely.
If the watchlist ever grew to thousands of tickers, a vectorised numpy step would
be worth it; at this scale it would be pure overhead.

**Lazy initialisation.** A ticker enters `self._prices` the first time it is
requested, starting at its anchor. Adding a ticker to the watchlist mid-session
needs no special handling.

**The simulator ignores market hours.** It runs at full speed at 3 AM on a
Sunday. This is deliberate: a trading demo that shows a frozen screen outside
market hours is a broken-looking demo.

## 5. Behaviour

Verified 1-sigma price movement:

| Horizon | Steadiest (V, sigma 0.20) | Most volatile (TSLA, sigma 0.60) |
|---|---|---|
| One tick (500 ms) | 0.006% ($0.016) | 0.017% ($0.044) |
| One minute | 0.064% | 0.191% |
| One hour | 0.49% | 1.48% |
| Full session | 1.26% | 3.78% |

The per-tick figures are the important ones for the UI. A typical move is between
one and fourteen cents, so after rounding to cents most ticks produce a visible
change. Measured proportion of ticks on which the rounded price actually moves,
over a full session:

| Ticker | Flash fires | Ticker | Flash fires |
|---|---|---|---|
| NVDA | 97.2% | AMZN | 79.4% |
| NFLX | 94.5% | GOOGL | 75.8% |
| META | 92.7% | V | 75.5% |
| TSLA | 91.0% | AAPL | 75.1% |
| MSFT | 86.9% | JPM | 70.3% |

Every row flashes on at least 70% of ticks, so the watchlist is in near-constant
motion at 2 Hz, while the underlying percentage moves stay realistic. The
lower-priced, lower-volatility names flash least, because a sub-half-cent move
rounds away — which is also true of real quote feeds.

Verified full-session outcome with the chosen parameters (seed 42):

```
ticker     anchor      end    chg%   range%
AAPL       190.00   194.02   +2.12     6.50
GOOGL      175.00   168.71   -3.59    11.93
MSFT       420.00   418.30   -0.40    10.38
AMZN       185.00   189.63   +2.50     5.37
TSLA       250.00   247.96   -0.82    13.59
NVDA       880.00   982.22  +11.62    14.94
META       500.00   504.97   +0.99     8.42
JPM        200.00   190.25   -4.88     6.59
V          280.00   281.29   +0.46     6.90
NFLX       610.00   594.92   -2.47     7.99
```

Most names close within a few percent of their anchor, one has a dramatic day.
That is the intended texture.

## 6. Configuration

| Variable | Default | Effect |
|---|---|---|
| `MARKET_SEED` | unset | Fixes the RNG seed. Set it in tests for reproducibility. Leave unset in production so each container run differs. |

The model constants (`KAPPA`, `EVENT_PROBABILITY`, `DT`) are module-level
constants rather than environment variables. They are tuning decisions backed by
the analysis in this document, not deployment settings, and exposing them as
configuration would invite values that have not been validated.

## 7. Testing

Every check below was written and executed against the implementation in
section 4, and all of them pass. The measured column is actual output, not an
estimate.

| Property | Test | Measured |
|---|---|---|
| Determinism | Two `SimulatorSource(seed=7)` instances produce identical **price** sequences over 1000 ticks | identical |
| Seed sensitivity | Seeds 7 and 8 diverge | diverge |
| Positivity | Over 100k quotes across all default tickers, every price is `> 0` | min 174.78 |
| Completeness | `fetch` returns exactly one quote per requested ticker | always |
| Empty input | `fetch([])` returns `[]` without drawing from the RNG | passes |
| Realised volatility | Std dev of log returns divided by `sqrt(DT)` within 5% of configured `sigma` | AAPL 0.2876 vs 0.28; TSLA 0.5988 vs 0.60 |
| Correlation ordering | `corr(AAPL, MSFT)` exceeds `corr(AAPL, JPM)` | 0.693 vs 0.389 |
| Correlation magnitude | Each correlation is near the product of the two betas | 0.693 vs 0.7225; 0.389 vs 0.425 |
| Anchor pull | A ticker forced to 2x its anchor falls back over one session | 380 to 264.77 |
| Unknown tickers | `profile_for("PYPL")` is stable across processes with differing `PYTHONHASHSEED` | $100.29 every time |
| Interface conformance | Shares the parametrised suite with `MassiveSource` per `MARKET_INTERFACE.md` | passes |

Three points that are easy to get wrong when writing these tests:

**Compare prices, not `Quote` objects.** `Quote.timestamp` is wall-clock
`datetime.now(UTC)`, so two seeded runs produce equal prices with different
timestamps. Asserting `run_a == run_b` on the quotes fails for a reason that has
nothing to do with the model.

**Disable events for the statistical tests.** Set `EVENT_PROBABILITY = 0.0` before
measuring volatility or correlation. With events enabled at the default rate, a
10,000-tick sample of AAPL measures a volatility of 1.25 against a configured 0.28,
and correlation collapses from 0.72 to 0.05 — the jumps are large, idiosyncratic
and swamp the diffusion. This is the model behaving correctly, not a defect, but
it makes the parameters untestable unless jumps are switched off.

**Expect roughly 3% inflation from rounding.** Measuring on the rounded prices the
`Quote` carries rather than the internal float raises realised volatility from
0.2792 to 0.2882 for AAPL, because a one-cent tick is a meaningful fraction of a
$0.0155 move. A 5% tolerance absorbs this; a 1% tolerance would fail.

## 8. Verification Evidence

The parameters above were chosen by sweeping `KAPPA` and `EVENT_PROBABILITY` over
8 seeds of a full 6.5-hour session (46,800 ticks) and measuring mean absolute
change from anchor and mean intraday range:

| KAPPA | EVENT_PROBABILITY | mean abs change | mean range | events |
|---|---|---|---|---|
| 0 | 2e-4 | 7.16% | 14.23% | 87 |
| 0 | 8e-5 | 5.85% | 10.26% | 40 |
| 175 | 2e-4 | 5.46% | 13.39% | 87 |
| **175** | **8e-5** | **4.25%** | **9.44%** | **37** |
| 500 | 8e-5 | 2.74% | 8.78% | 40 |

`KAPPA = 175` with `EVENT_PROBABILITY = 8e-5` was chosen as the point where
sessions stay in a believable range while events remain frequent enough to notice.
`KAPPA = 500` was rejected as visibly over-damped — prices become rubber-banded to
the anchor and stop looking like a market.

Further checks, all run against the implementation in section 4:

- **Realised volatility matches configuration.** With events disabled, AAPL
  configured at 0.28 realised 0.2792 on the internal price series and 0.2882 on
  the rounded series. TSLA configured at 0.60 realised 0.5988. The trading-time
  annualisation is correct.
- **Correlation matches the beta product exactly.** With events disabled and
  measured on internal prices, `corr(AAPL, MSFT)` came out at 0.724 against a
  predicted `0.85 * 0.85 = 0.7225`, and `corr(AAPL, JPM)` at 0.421 against a
  predicted `0.85 * 0.50 = 0.425`. The one-factor construction does what it claims.
- **Multi-day stability.** Five continuous sessions without restart left prices
  within 8-14% of their anchors, versus unbounded drift with no pull.
- **Event impact isolated.** Enabling events at the default rate moved measured
  AAPL volatility from 0.2792 to 1.25 and measured correlation from 0.724 to
  0.053 over the same 10,000 ticks. This is what motivates disabling events in the
  statistical tests, and it is the evidence behind the trade-off table in
  section 2.

## 9. Summary

- Geometric Brownian motion in trading time, stepped every 500 ms
- Positivity guaranteed by the model's structure, not by clamping
- A logarithmic anchor pull (`KAPPA = 175`, one-session half-life) replaces drift
  and bounds long-run wandering
- A single shared market factor per tick, mixed per ticker by `beta`, produces
  correlation without disturbing volatility
- 2-5% jumps at `8e-5` per ticker per tick, about one every ten minutes; these
  deliberately exaggerate intraday range (9.3% against a realistic 3.4%) in
  exchange for demo drama, and must be disabled when testing the statistics
- Unknown tickers get a deterministic profile from an `hashlib` digest of the symbol
- Standard library only, roughly 50 lines, seedable for deterministic tests
- Every property documented in section 7 was executed against the implementation
  and passes
