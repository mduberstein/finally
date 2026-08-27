import { describe, expect, it } from "vitest";

import { computeSparkline, formatCurrency, toTwo } from "../src/lib/utils";

describe("utils", () => {
  it("formats currency", () => {
    expect(formatCurrency(1234.567)).toBe("$1,234.57");
    expect(formatCurrency(-0.5)).toBe("-$0.50");
  });

  it("formats decimals", () => {
    expect(toTwo(1.987)).toBe("1.99");
    expect(toTwo(-1.111)).toBe("-1.11");
  });

  it("builds sparkline path", () => {
    const path = computeSparkline([10, 12, 11, 14]);
    expect(path.startsWith("M ")).toBe(true);
  });
});
