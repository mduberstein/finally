import { describe, expect, it } from "vitest";

import { directionGlyph, FLASH_DURATION_MS, isFlashActive, nextFlashState } from "./flash";

describe("nextFlashState", () => {
  it("starts a state with direction up and startedAt now for an up tick from null", () => {
    const state = nextFlashState(null, "up", 1000);
    expect(state).toEqual({ direction: "up", startedAt: 1000 });
  });

  it("starts a state with direction down and startedAt now for a down tick from null", () => {
    const state = nextFlashState(null, "down", 1000);
    expect(state).toEqual({ direction: "down", startedAt: 1000 });
  });

  it("returns null for a flat tick from null — an unchanged price never starts a flash", () => {
    expect(nextFlashState(null, "flat", 1000)).toBeNull();
  });

  it("returns the existing state unchanged for a flat tick — flat neither starts nor cancels", () => {
    const existing = { direction: "up" as const, startedAt: 1000 };
    expect(nextFlashState(existing, "flat", 1200)).toBe(existing);
  });

  it("restarts the flash from full intensity when a same-direction tick arrives inside the window", () => {
    const existing = { direction: "up" as const, startedAt: 1000 };
    expect(nextFlashState(existing, "up", 1200)).toEqual({ direction: "up", startedAt: 1200 });
  });

  it("switches direction and restarts startedAt when the direction reverses", () => {
    const existing = { direction: "up" as const, startedAt: 1000 };
    expect(nextFlashState(existing, "down", 1200)).toEqual({ direction: "down", startedAt: 1200 });
  });
});

describe("isFlashActive", () => {
  it("is true just before the fade window elapses", () => {
    expect(isFlashActive({ direction: "up", startedAt: 1000 }, 1499)).toBe(true);
  });

  it("is false exactly at FLASH_DURATION_MS", () => {
    expect(isFlashActive({ direction: "up", startedAt: 1000 }, 1500)).toBe(false);
  });

  it("is false for a null state", () => {
    expect(isFlashActive(null, 1000)).toBe(false);
  });
});

describe("directionGlyph", () => {
  it("returns the up triangle for up", () => {
    expect(directionGlyph("up")).toBe("▲");
  });

  it("returns the down triangle for down", () => {
    expect(directionGlyph("down")).toBe("▼");
  });

  it("returns an empty string for flat", () => {
    expect(directionGlyph("flat")).toBe("");
  });
});

describe("FLASH_DURATION_MS", () => {
  it("is 500", () => {
    expect(FLASH_DURATION_MS).toBe(500);
  });
});
