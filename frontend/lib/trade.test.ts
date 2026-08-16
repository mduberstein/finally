import { describe, expect, it } from "vitest";

import { MALFORMED_INPUT_MESSAGE, tradeErrorMessage, validateTradeInput } from "./trade";

describe("validateTradeInput", () => {
  it("is not ok for both fields empty", () => {
    const result = validateTradeInput("", "");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.message).toBe(MALFORMED_INPUT_MESSAGE);
  });

  it("is not ok when only the ticker is filled", () => {
    const result = validateTradeInput("AAPL", "");
    expect(result.ok).toBe(false);
  });

  it("is not ok when only the quantity is filled", () => {
    const result = validateTradeInput("", "10");
    expect(result.ok).toBe(false);
  });

  it("is not ok for a zero quantity", () => {
    const result = validateTradeInput("AAPL", "0");
    expect(result.ok).toBe(false);
  });

  it("is not ok for a negative quantity", () => {
    const result = validateTradeInput("AAPL", "-3");
    expect(result.ok).toBe(false);
  });

  it("is not ok for a fractional quantity", () => {
    const result = validateTradeInput("AAPL", "2.5");
    expect(result.ok).toBe(false);
  });

  it("is ok and normalises a lowercase ticker and numeric quantity", () => {
    const result = validateTradeInput("aapl", "10");
    expect(result).toEqual({ ok: true, ticker: "AAPL", quantity: 10 });
  });
});

describe("tradeErrorMessage", () => {
  it("returns the insufficient-cash sentence with the cash figure interpolated", () => {
    const message = tradeErrorMessage({
      code: "insufficient_cash",
      ticker: "AAPL",
      cost: 5000,
      cash_balance: 1234.5,
    });
    expect(message).toBe("Not enough cash — this trade costs more than your $1,234.50 available.");
  });

  it("returns the overselling sentence naming the owned quantity and ticker", () => {
    const message = tradeErrorMessage({
      code: "insufficient_shares",
      ticker: "AAPL",
      owned: 3,
    });
    expect(message).toBe("You only own 3 shares of AAPL.");
  });

  it("returns the untradable-ticker sentence naming the ticker", () => {
    const message = tradeErrorMessage({ code: "untradable_ticker", ticker: "ZZZZ" });
    expect(message).toBe("ZZZZ isn't on your watchlist — trade one of the tickers shown above.");
  });

  it("returns a neutral fallback for an unrecognised code", () => {
    const message = tradeErrorMessage({ code: "something_else" });
    expect(message).not.toContain("undefined");
    expect(message).not.toContain("{");
    expect(message.length).toBeGreaterThan(0);
  });

  it("returns a neutral fallback for a malformed payload", () => {
    const message = tradeErrorMessage(null);
    expect(message).not.toContain("undefined");
    expect(message.length).toBeGreaterThan(0);
  });
});
