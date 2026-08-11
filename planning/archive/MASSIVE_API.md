# Massive API Reference (formerly Polygon.io)

Research notes for retrieving real-time and end-of-day prices for multiple tickers.
Everything here was verified against `massive.com/docs` and against the installed
`massive` Python package (version 2.8.0) in July 2026.

## 1. What Massive Is

Polygon.io rebranded to **Massive.com** on 30 October 2025. Existing API keys,
accounts and integrations continue to work unchanged.

- Base URL: `https://api.massive.com`
- Legacy base URL `https://api.polygon.io` remains supported "for an extended period"
- Docs: https://massive.com/docs
- Official Python client: `massive` on PyPI (supersedes `polygon-api-client`)

The URL paths did not change in the rebrand. Endpoints are still versioned `/v1`,
`/v2`, `/v3` exactly as they were under Polygon.

## 2. Authentication

The API key is accepted two ways:

```bash
# Preferred: bearer header
curl -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT"

# Also supported: query parameter
curl "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT&apiKey=$MASSIVE_API_KEY"
```

The official Python client uses the bearer header and reads the environment
variable `MASSIVE_API_KEY` when no key is passed to the constructor. That is the
same variable name this project already specifies in `PLAN.md`, so no mapping is
needed.

Prefer the header form. The query-parameter form leaks the key into access logs,
proxy logs and browser history.

## 3. Plans, Rate Limits and Data Freshness

This is the single most important section for our design, because the free tier
**cannot** serve live intraday prices.

| Plan | Price | Requests/min | Data freshness | Snapshot endpoints |
|---|---|---|---|---|
| Stocks Basic | Free | 5 | End of day | Not included |
| Stocks Starter | $29/mo | Unlimited | 15-minute delayed | Included |
| Stocks Developer | $79/mo | Unlimited | 15-minute delayed | Included |
| Stocks Advanced | $199/mo | Unlimited | Real-time | Included |

Notes:

- The free Basic tier is **end-of-day only** and **excludes the snapshot family**.
  A Basic key can still read aggregates (previous day bar, daily ticker summary,
  daily market summary), so it can price a portfolio off the last close — but the
  prices will not move during the trading day.
- "Unlimited" on paid tiers is not truly unlimited: Massive asks that clients stay
  under roughly 100 requests/second and monitors for abuse.
- Exceeding the limit returns **HTTP 429**. The official client automatically
  retries 429 (and 413, 499, 500, 502, 503, 504) three times with exponential
  backoff (factor 0.1).

Consequence for FinAlly: a free-tier key produces a flat, non-moving watchlist.
The simulator is the better default for demos, which is exactly what `PLAN.md`
already specifies.

## 4. The Endpoints That Matter

### 4.1 Full Market Snapshot — the multi-ticker workhorse

**This is the endpoint to use for live multi-ticker polling.** One request returns
every watchlist ticker, so a 10-ticker watchlist costs one call, not ten.

```
GET /v2/snapshot/locale/us/markets/stocks/tickers
```

| Parameter | Type | Notes |
|---|---|---|
| `tickers` | string | Case-sensitive comma-separated list, e.g. `AAPL,TSLA,GOOG`. Omit or leave empty to return all 10,000+ tickers. |
| `include_otc` | boolean | Include OTC securities. Default `false`. |

Requires Stocks Starter or higher.

Response shape (fields verified against the documented sample):

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
      "min":     { "o": 120.435, "h": 120.468, "l": 120.37, "c": 120.4201,
                   "v": 270796, "av": 28724441, "vw": 120.4129, "n": 762,
                   "t": 1684428720000 },
      "lastTrade": { "p": 120.47, "s": 236, "t": 1605195918306274000, "x": 10, "i": "4046", "c": [14, 41] },
      "lastQuote": { "p": 120.46, "s": 8, "P": 120.47, "S": 4, "t": 1605195918507251700 }
    }
  ]
}
```

Field meanings:

| Field | Meaning |
|---|---|
| `day` | Today's aggregate bar so far (open/high/low/close/volume/VWAP) |
| `prevDay` | The previous trading day's completed bar |
| `min` | The most recent one-minute bar; `av` is accumulated day volume |
| `lastTrade.p` | Price of the most recent trade — the best "current price" |
| `lastQuote.p` / `.P` | Bid price / ask price (lowercase = bid, uppercase = ask) |
| `todaysChange` | Absolute change vs previous close |
| `todaysChangePerc` | Percent change vs previous close |
| `updated` | Last update, Unix **nanoseconds** |

**Timestamp units are inconsistent and this is a real trap.** `lastTrade.t`,
`lastQuote.t` and `updated` are nanoseconds. `min.t` is milliseconds. Always
divide explicitly rather than guessing.

**The zero-value gotcha.** Snapshot data is cleared daily at 3:30 AM ET and only
repopulates as exchanges report, starting as early as 4:00 AM ET. Between those
times, and on weekends and holidays, `day.c` and `min.c` are `0`. Never read
`day.c` blindly. Use a fallback ladder:

```python
price = (
    snap.get("lastTrade", {}).get("p")
    or snap.get("min", {}).get("c")
    or snap.get("day", {}).get("c")
    or snap.get("prevDay", {}).get("c")
)
```

`prevDay.c` is the only field that is reliably non-zero around the clock.

### 4.2 Unified Snapshot — the v3 alternative

```
GET /v3/snapshot?ticker.any_of=AAPL,MSFT,NVDA
```

Accepts up to **250 tickers** per request via `ticker.any_of`. Returns a flatter,
better-named schema (`last_trade.price`, `last_quote.bid`, `session`,
`market_status`) and spans multiple asset classes. Requires Starter or higher.

It is the more modern endpoint, but for a stocks-only watchlist it offers no
practical advantage over the v2 full market snapshot, and it adds pagination
handling. We use v2.

### 4.3 Daily Market Summary — the free-tier workhorse

```
GET /v2/aggs/grouped/locale/us/market/stocks/{date}
```

Returns the daily OHLC bar for **every** U.S. stock on one date in a single
request. Available on **all plans including free Basic**.

| Parameter | Type | Notes |
|---|---|---|
| `date` | string | `YYYY-MM-DD` |
| `adjusted` | boolean | Split-adjusted. Default `true`. |
| `include_otc` | boolean | Default `false`. |

```json
{
  "status": "OK",
  "adjusted": true,
  "queryCount": 10537,
  "resultsCount": 10537,
  "results": [
    { "T": "AAPL", "o": 115.55, "h": 117.59, "l": 114.13, "c": 115.97,
      "v": 131704427, "vw": 116.3058, "t": 1605042000000, "n": 421317 }
  ]
}
```

This is the correct free-tier strategy: one call per day gives closing prices for
the entire watchlist without touching the 5-per-minute budget. Filter the
`results` array client-side for the tickers we care about.

Note that `{date}` must be a trading day. Requesting a weekend or holiday returns
`"resultsCount": 0` with an empty `results` array rather than an error, so walk
back day by day until results appear.

### 4.4 Previous Day Bar

```
GET /v2/aggs/ticker/{stocksTicker}/prev
```

Returns the prior trading day's bar for one ticker. Available on all plans.
Handles the weekend/holiday walk-back automatically, which the grouped endpoint
does not.

```json
{
  "ticker": "AAPL", "status": "OK", "adjusted": true, "resultsCount": 1,
  "results": [
    { "T": "AAPL", "o": 115.55, "h": 117.59, "l": 114.13, "c": 115.97,
      "v": 131704427, "vw": 116.3058, "t": 1605042000000, "n": null }
  ]
}
```

Costs one request per ticker, so a 10-ticker watchlist is 10 requests — twice the
free tier's per-minute budget. Prefer 4.3 when pricing more than a few tickers.

### 4.5 Daily Ticker Summary

```
GET /v1/open-close/{stocksTicker}/{date}
```

Open/close for one ticker on one date, including pre-market and after-hours
prices. Available on all plans. Uses spelled-out field names, unlike the
single-letter aggregate schema.

```json
{
  "status": "OK", "symbol": "AAPL", "from": "2023-01-09",
  "open": 324.66, "high": 326.2, "low": 322.3, "close": 325.12,
  "volume": 26122646, "preMarket": 324.5, "afterHours": 322.1
}
```

### 4.6 Other Endpoints (not used by this project)

| Endpoint | Path | Why we skip it |
|---|---|---|
| Single Ticker Snapshot | `/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}` | One call per ticker; the multi-ticker form is strictly better |
| Last Trade | `/v2/last/trade/{ticker}` | One call per ticker |
| Last Quote | `/v2/last/nbbo/{ticker}` | We show trade prices, not bid/ask |
| Custom Bars | `/v2/aggs/ticker/{ticker}/range/{mult}/{timespan}/{from}/{to}` | Useful later for historical charts |
| Top Market Movers | `/v2/snapshot/locale/us/markets/stocks/{direction}` | Not in scope |
| Market Status | `/v1/marketstatus/now` | Useful to detect closed markets |
| WebSocket | `wss://socket.massive.com/stocks` | `PLAN.md` deliberately chose REST polling |

## 5. Python Client Library

### Installation

```bash
uv add massive
```

Verified package facts:

- PyPI name `massive`, version **2.8.0**, requires Python `>=3.9,<4.0`
- Import is `from massive import RESTClient`
- Default base URL is `https://api.massive.com`
- Sends `Authorization: Bearer <key>`
- Raises `AuthError` if no key is passed and `MASSIVE_API_KEY` is unset

The older `polygon-api-client` (version 1.16.3, `from polygon import RESTClient`)
is the pre-rebrand package and is now frozen. Use `massive`.

### Multi-ticker snapshot

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

snapshots = client.get_snapshot_all("stocks", tickers=["AAPL", "MSFT", "NVDA"])

for snap in snapshots:
    price = snap.last_trade.price if snap.last_trade else snap.prev_day.close
    print(f"{snap.ticker:6s} {price:10.2f} {snap.todays_change_percent:+6.2f}%")
```

Verified signature:

```python
RESTClient.get_snapshot_all(
    market_type: str | SnapshotMarketType,
    tickers: str | list[str] | None = None,
    params: dict | None = None,
    raw: bool = False,
    include_otc: bool | None = False,
    options: RequestOptionBuilder | None = None,
) -> list[TickerSnapshot] | HTTPResponse
```

`TickerSnapshot` exposes snake_case attributes, not the raw JSON keys:

```
day, last_quote, last_trade, min, prev_day, ticker,
todays_change, todays_change_percent, updated, fair_market_value
```

Nested bars (`day`, `prev_day`, `min`) expose `open`, `high`, `low`, `close`,
`volume`, `vwap`, `timestamp`. `min` additionally exposes `accumulated_volume`
and `transactions`.

### Free-tier daily bars

```python
from datetime import date, timedelta

def latest_grouped_close(client, tickers, max_lookback=5):
    """Walk back to the most recent trading day and return {ticker: close}."""
    wanted = set(tickers)
    day = date.today()
    for _ in range(max_lookback):
        bars = client.get_grouped_daily_aggs(day.isoformat())
        if bars:
            return {b.ticker: b.close for b in bars if b.ticker in wanted}
        day -= timedelta(days=1)
    return {}
```

Verified signature:

```python
RESTClient.get_grouped_daily_aggs(
    date: str | datetime.date,
    adjusted: bool | None = None,
    params: dict | None = None,
    raw: bool = False,
    locale: str = "us",
    market_type: str = "stocks",
    include_otc: bool = False,
    options: RequestOptionBuilder | None = None,
) -> list[GroupedDailyAgg] | HTTPResponse
```

### The blocking-I/O problem

**The official client is synchronous.** It is built on `urllib3.PoolManager`, not
`httpx.AsyncClient` or `aiohttp`. Calling it directly from a FastAPI coroutine
blocks the event loop and stalls every open SSE connection.

If we use the client, every call must be offloaded:

```python
snapshots = await asyncio.to_thread(client.get_snapshot_all, "stocks", tickers)
```

### Raw HTTP alternative

Because we need exactly one endpoint, calling it directly with `httpx` is
simpler than pulling in a client library plus a thread-offload wrapper. It is
natively async and has no hidden retry behaviour.

```python
import httpx

BASE = "https://api.massive.com"

async def fetch_snapshots(api_key: str, tickers: list[str]) -> dict[str, float]:
    """Return {ticker: price} for the given tickers."""
    url = f"{BASE}/v2/snapshot/locale/us/markets/stocks/tickers"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            url,
            params={"tickers": ",".join(tickers)},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        payload = response.json()

    return {
        item["ticker"]: _extract_price(item)
        for item in payload.get("tickers", [])
    }


def _extract_price(item: dict) -> float:
    """Most recent usable price, tolerating the pre-open zero values."""
    return (
        item.get("lastTrade", {}).get("p")
        or item.get("min", {}).get("c")
        or item.get("day", {}).get("c")
        or item["prevDay"]["c"]
    )
```

`MARKET_INTERFACE.md` recommends this raw approach.

## 6. Error Handling

| Status | Meaning | Response to it |
|---|---|---|
| 200 with `"status": "OK"` | Success | Normal path |
| 401 | Missing or invalid key | Fatal config error; log clearly and fall back to the simulator |
| 403 | Key valid, plan does not cover the endpoint | Expected on a free key hitting snapshots; fall back |
| 429 | Rate limit exceeded | Back off and lengthen the poll interval |
| 5xx | Massive-side fault | Retry with backoff; serve the last cached price meanwhile |

A 200 response can still carry `"status": "NOT_AUTHORIZED"` or `"ERROR"` in the
body, so check the `status` field as well as the HTTP code.

Unknown or delisted tickers are silently omitted from the `tickers` array rather
than raising an error. Always compare the returned set against the requested set
instead of assuming they match.

## 7. Summary of Decisions for FinAlly

1. Use `GET /v2/snapshot/locale/us/markets/stocks/tickers` with a comma-separated
   `tickers` list. One request per poll regardless of watchlist size.
2. Authenticate with `Authorization: Bearer`, reading `MASSIVE_API_KEY`.
3. Call it with raw `httpx` rather than the `massive` client, because the client
   is synchronous and we need exactly one endpoint.
4. Extract price via the `lastTrade -> min -> day -> prevDay` fallback ladder.
5. Poll every 15 seconds by default, configurable.
6. Treat 401/403/429 as "degrade gracefully", never as a crash.
7. Expect a free Basic key to fail on snapshots; the simulator remains the default
   experience.

## Sources

- [Polygon.io is Now Massive](https://massive.com/blog/polygon-is-now-massive)
- [Stocks REST API Overview](https://massive.com/docs/rest/stocks/overview)
- [Full Market Snapshot](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot)
- [Single Ticker Snapshot](https://massive.com/docs/rest/stocks/snapshots/single-ticker-snapshot)
- [Unified Snapshot](https://massive.com/docs/rest/stocks/snapshots/unified-snapshot)
- [Daily Market Summary](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary)
- [Previous Day Bar](https://massive.com/docs/rest/stocks/aggregates/previous-day-bar)
- [Daily Ticker Summary](https://massive.com/docs/rest/stocks/aggregates/daily-ticker-summary)
- [REST request limits](https://massive.com/knowledge-base/article/what-is-the-request-limit-for-polygons-restful-apis)
- [Massive pricing](https://massive.com/pricing)
- [Official Python client](https://github.com/massive-com/client-python)
- [`massive` on PyPI](https://pypi.org/project/massive/)
