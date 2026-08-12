import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PositionsTable } from "./PositionsTable";
import { emit, makeTick, startStream, stopStream } from "@/test/stream";
import type { Position } from "@/lib/types";

afterEach(stopStream);

const AAPL: Position = {
  ticker: "AAPL",
  quantity: 10,
  avg_cost: 190,
  current_price: 195,
  market_value: 1950,
  unrealized_pnl: 50,
  unrealized_pnl_percent: 2.63,
  weight: 0.195,
};

describe("PositionsTable", () => {
  it("shows an empty state with no positions", () => {
    render(<PositionsTable positions={[]} selected={null} onSelect={vi.fn()} />);
    expect(screen.getByTestId("positions-empty")).toBeInTheDocument();
  });

  it("displays quantity, cost, value and unrealized P&L", () => {
    render(<PositionsTable positions={[AAPL]} selected={null} onSelect={vi.fn()} />);
    const row = screen.getByTestId("position-row-AAPL");

    expect(row).toHaveTextContent("10");
    expect(row).toHaveTextContent("190.00");
    expect(row).toHaveTextContent("1,950.00");
    expect(screen.getByTestId("position-pnl-AAPL")).toHaveTextContent("+50.00");
    expect(row).toHaveTextContent("+2.63%");
  });

  it("marks the position to the live price", () => {
    startStream();
    render(<PositionsTable positions={[AAPL]} selected={null} onSelect={vi.fn()} />);

    emit(makeTick("AAPL", 200, "up", 195));

    const row = screen.getByTestId("position-row-AAPL");
    expect(screen.getByTestId("position-price-AAPL")).toHaveTextContent("200.00");
    expect(row).toHaveTextContent("2,000.00");
    expect(screen.getByTestId("position-pnl-AAPL")).toHaveTextContent("+100.00");
    expect(row).toHaveTextContent("+5.26%");
  });

  it("reports a loss with the down tone", () => {
    const losing: Position = { ...AAPL, avg_cost: 200, current_price: 190 };
    render(<PositionsTable positions={[losing]} selected={null} onSelect={vi.fn()} />);

    const pnl = screen.getByTestId("position-pnl-AAPL");
    expect(pnl).toHaveTextContent("-100.00");
    expect(pnl.className).toContain("text-down");
  });
});
