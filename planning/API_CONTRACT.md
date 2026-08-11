# API Contract

The frozen interface between `frontend/` and `backend/`. Every field below is
part of the contract: the Backend API Engineer and LLM Engineer produce these
shapes, the Frontend Engineer and Integration Tester consume them.

**Changing this file requires messaging every agent that reads the affected
endpoint.** Do not silently rename a field — a rename that isn't announced is a
broken frontend.

Paths and the database schema come from `PLAN.md` §7-8. This document only
pins down the JSON shapes that `PLAN.md` leaves open.

## Conventions

- All money and quantity values are JSON numbers (float). Quantities support
  fractional shares.
- All timestamps are ISO 8601 strings, UTC.
- Percentages are whole-number percent (`2.63` means 2.63%), not fractions.
- Errors use FastAPI's default shape: `{"detail": "human readable reason"}`.
  Business-rule failures are `400`; missing resources `404`; malformed request
  bodies `422` (Pydantic default).
- `user_id` never appears in any request or response. It is `"default"`
  server-side and invisible to the client.

## `GET /api/health`

```json
{ "status": "ok" }
```

## `GET /api/stream/prices` (SSE — already implemented)

Implemented in `backend/app/market/stream.py`. Event name is `price`, `data` is
a JSON string. One event per ticker whose price changed; a full snapshot of all
tickers is sent when a client first connects.

```json
{
  "ticker": "AAPL",
  "price": 195.12,
  "previous_price": 194.98,
  "change": 0.14,
  "change_percent": 0.0718,
  "direction": "up",
  "timestamp": "2026-08-11T12:00:00.500000+00:00"
}
```

`direction` is one of `"up"`, `"down"`, `"flat"`. `change_percent` here is
**tick-over-tick**, not daily.

**Session change %**: `PLAN.md` §10 asks for a "daily change %" in the
watchlist. The simulator has no daily open, so the frontend computes change
against the first price it saw for that ticker since page load, consistent with
how sparklines accumulate. Label it "since open" in the UI, not "daily".

## `GET /api/portfolio`

```json
{
  "cash_balance": 8050.0,
  "positions_value": 1950.0,
  "total_value": 10000.0,
  "total_unrealized_pnl": 50.0,
  "total_unrealized_pnl_percent": 2.63,
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 10.0,
      "avg_cost": 190.0,
      "current_price": 195.0,
      "market_value": 1950.0,
      "unrealized_pnl": 50.0,
      "unrealized_pnl_percent": 2.63,
      "weight": 0.195
    }
  ]
}
```

- `current_price` comes from the shared `PriceCache`. If a ticker has no cached
  price yet, fall back to `avg_cost` so the portfolio never renders as `null`.
- `weight` is `market_value / total_value`, a fraction in `[0, 1]` — the
  heatmap sizes rectangles by it.
- `positions` is `[]` when nothing is held.

## `POST /api/portfolio/trade`

Request:

```json
{ "ticker": "AAPL", "quantity": 10, "side": "buy" }
```

`side` is `"buy"` or `"sell"`. `quantity` must be `> 0` (422 otherwise).
`ticker` is upper-cased server-side.

Response `200`:

```json
{
  "trade": {
    "id": "uuid",
    "ticker": "AAPL",
    "side": "buy",
    "quantity": 10.0,
    "price": 195.0,
    "executed_at": "2026-08-11T12:00:00+00:00"
  },
  "cash_balance": 8050.0,
  "position": {
    "ticker": "AAPL", "quantity": 10.0, "avg_cost": 195.0,
    "current_price": 195.0, "market_value": 1950.0,
    "unrealized_pnl": 0.0, "unrealized_pnl_percent": 0.0, "weight": 0.195
  }
}
```

`position` is `null` when a sell closes the position entirely.

Failure cases, all `400` with `detail`:

| Condition | `detail` |
|---|---|
| Not enough cash | `Insufficient cash: need $1950.00, have $100.00` |
| Not enough shares | `Insufficient shares: tried to sell 10 AAPL, hold 3` |
| No price available | `No price available for ZZZZ` |

The message text is read by the LLM and shown to the user, so keep it specific.

## `GET /api/portfolio/history`

Optional query param `limit` (default 500, newest N returned in ascending time
order).

```json
{
  "snapshots": [
    { "total_value": 10000.0, "recorded_at": "2026-08-11T12:00:00+00:00" }
  ]
}
```

## `GET /api/watchlist`

```json
{
  "tickers": [
    {
      "ticker": "AAPL",
      "added_at": "2026-08-11T12:00:00+00:00",
      "price": 195.0,
      "previous_price": 194.9,
      "change": 0.1,
      "change_percent": 0.0513,
      "direction": "up"
    }
  ]
}
```

Price fields are `null` for a ticker the cache hasn't seen yet (a just-added
ticker, before the next feed poll). The frontend must render that state without
crashing — the SSE stream fills it in shortly after.

## `POST /api/watchlist`

Request `{ "ticker": "pypl" }` — upper-cased server-side.

Response `201`: the same object shape as one entry of `GET /api/watchlist`.

- `409` if the ticker is already on the watchlist.
- `422` if the ticker isn't 1-5 letters.

## `DELETE /api/watchlist/{ticker}`

`204` with no body. `404` if the ticker isn't on the watchlist.

Removing a ticker does **not** close any position in it.

## `POST /api/chat`

Request `{ "message": "buy 10 shares of Apple" }`.

Response `200`:

```json
{
  "message": "Bought 10 AAPL at $195.00. That's 19.5% of your portfolio.",
  "actions": [
    {
      "type": "trade",
      "status": "executed",
      "detail": "Bought 10 AAPL @ $195.00",
      "ticker": "AAPL"
    },
    {
      "type": "watchlist",
      "status": "failed",
      "detail": "PYPL is already on the watchlist",
      "ticker": "PYPL"
    }
  ],
  "created_at": "2026-08-11T12:00:00+00:00"
}
```

- `type` is `"trade"` or `"watchlist"`. `status` is `"executed"` or `"failed"`.
- `actions` is `[]` when the assistant only talked.
- `detail` is rendered inline in the chat panel as a confirmation chip.
- The endpoint always returns `200` when the LLM responds. An LLM or provider
  failure is `503` with `detail`.

## `GET /api/chat/history`

**Addition beyond `PLAN.md` §8**, needed because `chat_messages` is persisted
and the panel must repopulate on reload. Optional `limit` (default 50).

```json
{
  "messages": [
    {
      "role": "user",
      "content": "buy 10 shares of Apple",
      "actions": [],
      "created_at": "2026-08-11T12:00:00+00:00"
    },
    {
      "role": "assistant",
      "content": "Bought 10 AAPL at $195.00.",
      "actions": [ { "type": "trade", "status": "executed", "detail": "Bought 10 AAPL @ $195.00", "ticker": "AAPL" } ],
      "created_at": "2026-08-11T12:00:01+00:00"
    }
  ]
}
```

Ascending time order. `actions` is `[]` for user messages.
