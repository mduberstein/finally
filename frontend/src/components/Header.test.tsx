import { afterEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "./Header";
import { FakeEventSource, emit, failStream, makeTick, startStream, stopStream } from "@/test/stream";
import type { Portfolio } from "@/lib/types";

afterEach(stopStream);

const PORTFOLIO: Portfolio = {
  cash_balance: 1000,
  positions_value: 1000,
  total_value: 2000,
  total_unrealized_pnl: 0,
  total_unrealized_pnl_percent: 0,
  positions: [
    {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 100,
      current_price: 100,
      market_value: 1000,
      unrealized_pnl: 0,
      unrealized_pnl_percent: 0,
      weight: 0.5,
    },
  ],
};

describe("Header", () => {
  it("renders placeholders before the portfolio loads", () => {
    render(<Header portfolio={null} />);
    expect(screen.getByTestId("header-total-value")).toHaveTextContent("—");
    expect(screen.getByTestId("header-cash")).toHaveTextContent("—");
  });

  it("marks total value to the live price", () => {
    startStream();
    render(<Header portfolio={PORTFOLIO} />);

    expect(screen.getByTestId("header-total-value")).toHaveTextContent("2,000.00");

    emit(makeTick("AAPL", 110, "up", 100));

    expect(screen.getByTestId("header-total-value")).toHaveTextContent("2,100.00");
    expect(screen.getByTestId("header-pnl")).toHaveTextContent("+100.00");
    expect(screen.getByTestId("header-pnl")).toHaveTextContent("+10.00%");
    expect(screen.getByTestId("header-cash")).toHaveTextContent("1,000.00");
  });

  it("tracks the connection state", () => {
    startStream();
    render(<Header portfolio={PORTFOLIO} />);

    expect(screen.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");

    failStream(FakeEventSource.CLOSED);

    expect(screen.getByTestId("connection-status")).toHaveAttribute("data-status", "disconnected");
  });
});
