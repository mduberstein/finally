import { describe, expect, it } from "vitest";

import { formatPercent, formatPrice } from "./format";

describe("formatPrice", () => {
  it("returns exactly 2 decimal places", () => {
    expect(formatPrice(190.5)).toBe("190.50");
  });

  it("adds a thousands separator for 4-plus digit prices", () => {
    expect(formatPrice(1234.5)).toBe("1,234.50");
  });

  it("returns an em dash for null", () => {
    expect(formatPrice(null)).toBe("—");
  });

  it("returns an em dash for undefined", () => {
    expect(formatPrice(undefined)).toBe("—");
  });
});

describe("formatPercent", () => {
  it("adds an explicit plus sign for positive values", () => {
    expect(formatPercent(1.2345)).toBe("+1.23%");
  });

  it("keeps the minus sign for negative values", () => {
    expect(formatPercent(-0.5)).toBe("-0.50%");
  });

  it("has no sign prefix on exact zero", () => {
    expect(formatPercent(0)).toBe("0.00%");
  });

  it("returns an em dash for null", () => {
    expect(formatPercent(null)).toBe("—");
  });

  it("returns an em dash for undefined", () => {
    expect(formatPercent(undefined)).toBe("—");
  });
});
