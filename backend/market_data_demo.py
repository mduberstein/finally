"""Command-line proof that the GBM market data simulator works.

Streams all 10 default tickers through a live Rich dashboard: current price,
tick-to-tick direction arrows, a rolling sparkline, and an event log for
notable single-tick moves ("drama events"). Runs for 60 seconds or until
Ctrl+C. Uses `SimulatorSource` and `PriceCache` from `app/market/` directly —
no FastAPI, no network.

    cd backend && uv run market_data_demo.py
"""

import asyncio
import time
from collections import deque

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from app.market import simulator as simulator_module
from app.market.cache import PriceCache
from app.market.seed_prices import PROFILES
from app.market.simulator import SimulatorSource

TICKERS = list(PROFILES.keys())

RUN_SECONDS = 60
SPARKLINE_WIDTH = 30
NOTABLE_CHANGE_PCT = 1.0
MAX_LOGGED_EVENTS = 8

DEMO_EVENT_PROBABILITY = 3e-4
# ~4x the production default (`EVENT_PROBABILITY = 8e-5`). At the production
# rate a 60s run only expects ~1 drama event across all 10 tickers; this bumps
# it to a handful so the event log actually has something to show, without
# touching how the jump itself is computed.

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: "deque[float] | list[float]") -> str:
    """Render a list of prices as a unicode block sparkline."""
    values = list(values)
    if len(values) < 2:
        return SPARK_CHARS[0] * len(values)
    lo, hi = min(values), max(values)
    if hi == lo:
        return SPARK_CHARS[len(SPARK_CHARS) // 2] * len(values)
    span = hi - lo
    levels = len(SPARK_CHARS) - 1
    return "".join(SPARK_CHARS[min(int((v - lo) / span * levels), levels)] for v in values)


def direction_arrow(direction: str) -> Text:
    if direction == "up":
        return Text("▲", style="bold green")
    if direction == "down":
        return Text("▼", style="bold red")
    return Text("►", style="dim")


def build_table(cache: PriceCache, history: dict, elapsed: float, remaining: float) -> Table:
    table = Table(
        title=f"FinAlly Market Data Simulator — live GBM feed "
        f"({elapsed:5.1f}s elapsed, {remaining:4.1f}s remaining)",
        expand=True,
    )
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Price", justify="right")
    table.add_column("Chg", justify="right")
    table.add_column("Chg %", justify="right")
    table.add_column("Dir", justify="center")
    table.add_column(f"Sparkline (last {SPARKLINE_WIDTH} ticks)")

    for ticker in TICKERS:
        update = cache.get(ticker)
        if update is None:
            table.add_row(ticker, "…", "", "", "", "")
            continue
        style = {"up": "green", "down": "red"}.get(update.direction, "white")
        table.add_row(
            ticker,
            f"${update.price:,.2f}",
            Text(f"{update.change:+.2f}", style=style),
            Text(f"{update.change_percent:+.2f}%", style=style),
            direction_arrow(update.direction),
            Text(sparkline(history[ticker]), style="cyan"),
        )
    return table


def build_event_log(events: "deque[tuple]") -> Panel:
    if not events:
        body = f"[dim]Watching for single-tick moves ≥ {NOTABLE_CHANGE_PCT:.1f}%…[/]"
    else:
        lines = [
            f"[dim]{ts}[/] {ticker:<6} {arrow} {pct:+.2f}%  (${before:,.2f} → ${after:,.2f})"
            for ts, ticker, arrow, pct, before, after in reversed(events)
        ]
        body = "\n".join(lines)
    return Panel(
        body,
        title="Event Log — notable price moves",
        border_style="yellow",
        height=MAX_LOGGED_EVENTS + 2,
    )


async def main() -> None:
    console = Console()

    # Amplify drama-event frequency for a livelier 60s demo; see docstring above.
    simulator_module.EVENT_PROBABILITY = DEMO_EVENT_PROBABILITY

    source = SimulatorSource()
    cache = PriceCache()
    history = {ticker: deque(maxlen=SPARKLINE_WIDTH) for ticker in TICKERS}
    events: deque = deque(maxlen=MAX_LOGGED_EVENTS)

    console.print("[bold]FinAlly market data simulator demo[/] — Ctrl+C to stop early\n")
    start = time.monotonic()

    with Live(console=console, refresh_per_second=4, screen=False) as live:
        try:
            while True:
                elapsed = time.monotonic() - start
                if elapsed >= RUN_SECONDS:
                    break

                quotes = await source.fetch(TICKERS)
                changed = cache.apply(quotes)

                for ticker in TICKERS:
                    update = cache.get(ticker)
                    if update is not None:
                        history[ticker].append(update.price)

                for update in changed:
                    if abs(update.change_percent) >= NOTABLE_CHANGE_PCT:
                        arrow = "▲" if update.direction == "up" else "▼"
                        events.append(
                            (
                                update.timestamp.strftime("%H:%M:%S"),
                                update.ticker,
                                arrow,
                                update.change_percent,
                                update.previous_price,
                                update.price,
                            )
                        )

                remaining = max(0.0, RUN_SECONDS - elapsed)
                live.update(
                    Group(build_table(cache, history, elapsed, remaining), build_event_log(events))
                )
                await asyncio.sleep(source.poll_interval)
        except KeyboardInterrupt:
            pass

    console.print(
        f"\n[bold]Demo complete[/] — ran {time.monotonic() - start:.1f}s, {len(events)} notable move(s) logged."
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
