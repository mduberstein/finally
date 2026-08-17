import { describe, expect, it } from "vitest";

import { clearSelectionIfRemoved } from "./selection";

describe("clearSelectionIfRemoved", () => {
  it("clears the selection when the removed ticker is the current one (WR-03)", () => {
    expect(clearSelectionIfRemoved("AAPL", "AAPL")).toBeNull();
  });

  it("preserves the selection when an unrelated ticker is removed", () => {
    expect(clearSelectionIfRemoved("AAPL", "TSLA")).toBe("AAPL");
  });

  it("stays null when nothing is selected", () => {
    expect(clearSelectionIfRemoved(null, "AAPL")).toBeNull();
  });

  it("returns the identical string reference when preserving the selection", () => {
    const current = "AAPL";
    expect(clearSelectionIfRemoved(current, "TSLA")).toBe(current);
  });
});
