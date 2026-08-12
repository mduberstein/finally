import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Watchlist } from "./Watchlist";
import { emit, makeTick, startStream, stopStream } from "@/test/stream";
import type { WatchlistEntry } from "@/lib/types";

afterEach(stopStream);

function entry(ticker: string, price: number | null): WatchlistEntry {
  return {
    ticker,
    added_at: "2026-08-11T12:00:00+00:00",
    price,
    previous_price: price,
    change: price == null ? null : 0,
    change_percent: price == null ? null : 0,
    direction: price == null ? null : "flat",
  };
}

function renderWatchlist(entries: WatchlistEntry[], overrides = {}) {
  const props = {
    entries,
    loading: false,
    selected: null,
    onSelect: vi.fn(),
    onAdd: vi.fn().mockResolvedValue(null),
    onRemove: vi.fn(),
    ...overrides,
  };
  render(<Watchlist {...props} />);
  return props;
}

describe("Watchlist", () => {
  it("renders a row per ticker with its REST price", () => {
    renderWatchlist([entry("AAPL", 195), entry("GOOGL", 175.5)]);

    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveTextContent("195.00");
    expect(screen.getByTestId("watchlist-price-GOOGL")).toHaveTextContent("175.50");
  });

  it("renders a freshly added ticker with no price yet", () => {
    renderWatchlist([entry("PYPL", null)]);

    expect(screen.getByTestId("watchlist-price-PYPL")).toHaveTextContent("—");
    expect(screen.getByTestId("watchlist-change-PYPL")).toHaveTextContent("—");
  });

  it("shows an empty state when nothing is watched", () => {
    renderWatchlist([]);
    expect(screen.getByTestId("watchlist-empty")).toBeInTheDocument();
  });

  it("takes the live price over the REST price and shows change since open", () => {
    startStream();
    renderWatchlist([entry("AAPL", 195)]);

    emit(makeTick("AAPL", 200));
    emit(makeTick("AAPL", 210, "up", 200));

    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveTextContent("210.00");
    expect(screen.getByTestId("watchlist-change-AAPL")).toHaveTextContent("+5.00%");
  });

  it("flashes the price cell on a change, then clears it", () => {
    vi.useFakeTimers();
    startStream();
    renderWatchlist([entry("AAPL", 195)]);

    emit(makeTick("AAPL", 195, "flat"));
    const cell = screen.getByTestId("watchlist-price-AAPL");
    expect(cell.className).toContain("flashable");
    expect(cell.className).not.toContain("flash-up");

    emit(makeTick("AAPL", 196, "up", 195));
    expect(screen.getByTestId("watchlist-price-AAPL").className).toContain("flash-up");

    // A re-render from an unchanged price must not wipe the painted class.
    emit(makeTick("AAPL", 196, "flat", 196));
    expect(screen.getByTestId("watchlist-price-AAPL").className).toContain("flash-up");

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.getByTestId("watchlist-price-AAPL").className).not.toContain("flash-up");

    emit(makeTick("AAPL", 195, "down", 196));
    expect(screen.getByTestId("watchlist-price-AAPL").className).toContain("flash-down");

    vi.useRealTimers();
  });

  it("selects a ticker when its row is clicked", async () => {
    const user = userEvent.setup();
    const props = renderWatchlist([entry("AAPL", 195)]);

    await user.click(screen.getByTestId("watchlist-row-AAPL"));
    expect(props.onSelect).toHaveBeenCalledWith("AAPL");
  });

  it("adds a ticker and clears the input", async () => {
    const user = userEvent.setup();
    const props = renderWatchlist([]);

    await user.type(screen.getByTestId("watchlist-add-input"), "pypl");
    await user.click(screen.getByTestId("watchlist-add-submit"));

    expect(props.onAdd).toHaveBeenCalledWith("PYPL");
    expect(screen.getByTestId("watchlist-add-input")).toHaveValue("");
  });

  it("shows the server's reason when an add is rejected", async () => {
    const user = userEvent.setup();
    renderWatchlist([], { onAdd: vi.fn().mockResolvedValue("AAPL is already on the watchlist") });

    await user.type(screen.getByTestId("watchlist-add-input"), "AAPL");
    await user.click(screen.getByTestId("watchlist-add-submit"));

    expect(screen.getByTestId("watchlist-add-error")).toHaveTextContent(
      "AAPL is already on the watchlist",
    );
  });

  it("removes a ticker without selecting it", async () => {
    const user = userEvent.setup();
    const props = renderWatchlist([entry("AAPL", 195)]);

    await user.click(screen.getByTestId("watchlist-remove-AAPL"));

    expect(props.onRemove).toHaveBeenCalledWith("AAPL");
    expect(props.onSelect).not.toHaveBeenCalled();
  });
});
