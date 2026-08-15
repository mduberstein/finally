import { describe, expect, it } from "vitest";

import {
  DISCONNECTED_AFTER_ERRORS,
  STALE_AFTER_MS,
  initialConnectionState,
  reduceConnection,
  statusLabel,
} from "./connection";

describe("initialConnectionState", () => {
  it("starts reconnecting with zero errors — not yet proven healthy", () => {
    const state = initialConnectionState(0);
    expect(state.status).toBe("reconnecting");
    expect(state.consecutiveErrors).toBe(0);
  });
});

describe("reduceConnection", () => {
  it("open transitions to connected with zero errors", () => {
    const initial = initialConnectionState(0);
    const state = reduceConnection(initial, { kind: "open" }, 1000);
    expect(state.status).toBe("connected");
    expect(state.consecutiveErrors).toBe(0);
  });

  it("message keeps connected and stamps lastMessageAt", () => {
    const initial = initialConnectionState(0);
    const connected = reduceConnection(initial, { kind: "open" }, 1000);
    const state = reduceConnection(connected, { kind: "message" }, 2000);
    expect(state.status).toBe("connected");
    expect(state.lastMessageAt).toBe(2000);
  });

  it("a single error downgrades connected to reconnecting", () => {
    const initial = initialConnectionState(0);
    const connected = reduceConnection(initial, { kind: "open" }, 1000);
    const state = reduceConnection(connected, { kind: "error" }, 3000);
    expect(state.status).toBe("reconnecting");
    expect(state.consecutiveErrors).toBe(1);
  });

  it("three consecutive errors reach disconnected", () => {
    let state = reduceConnection(initialConnectionState(0), { kind: "open" }, 1000);
    state = reduceConnection(state, { kind: "error" }, 2000);
    state = reduceConnection(state, { kind: "error" }, 3000);
    state = reduceConnection(state, { kind: "error" }, 4000);
    expect(state.status).toBe("disconnected");
    expect(state.consecutiveErrors).toBe(DISCONNECTED_AFTER_ERRORS);
  });

  it("recovers automatically from disconnected on open", () => {
    let state = reduceConnection(initialConnectionState(0), { kind: "open" }, 1000);
    state = reduceConnection(state, { kind: "error" }, 2000);
    state = reduceConnection(state, { kind: "error" }, 3000);
    state = reduceConnection(state, { kind: "error" }, 4000);
    expect(state.status).toBe("disconnected");
    state = reduceConnection(state, { kind: "open" }, 9000);
    expect(state.status).toBe("connected");
    expect(state.consecutiveErrors).toBe(0);
  });

  it("recovers automatically from disconnected on message", () => {
    let state = reduceConnection(initialConnectionState(0), { kind: "open" }, 1000);
    state = reduceConnection(state, { kind: "error" }, 2000);
    state = reduceConnection(state, { kind: "error" }, 3000);
    state = reduceConnection(state, { kind: "error" }, 4000);
    expect(state.status).toBe("disconnected");
    state = reduceConnection(state, { kind: "message" }, 9000);
    expect(state.status).toBe("connected");
    expect(state.consecutiveErrors).toBe(0);
  });

  it("a tick within the staleness window stays connected", () => {
    let state = reduceConnection(initialConnectionState(0), { kind: "open" }, 1000);
    state = reduceConnection(state, { kind: "message" }, 1000);
    state = reduceConnection(state, { kind: "tick" }, 5000);
    expect(state.status).toBe("connected");
  });

  it("a tick beyond the staleness window downgrades to reconnecting even though the socket believes it is open", () => {
    let state = reduceConnection(initialConnectionState(0), { kind: "open" }, 1000);
    state = reduceConnection(state, { kind: "message" }, 1000);
    state = reduceConnection(state, { kind: "tick" }, 1000 + STALE_AFTER_MS);
    expect(state.status).toBe("reconnecting");
  });

  it("a tick on a reconnecting state leaves it unchanged", () => {
    const initial = initialConnectionState(0);
    const state = reduceConnection(initial, { kind: "tick" }, 999999);
    expect(state.status).toBe("reconnecting");
    expect(state).toEqual(initial);
  });
});

describe("statusLabel", () => {
  it("maps each status to its fixed label", () => {
    expect(statusLabel("connected")).toBe("Connected");
    expect(statusLabel("reconnecting")).toBe("Reconnecting");
    expect(statusLabel("disconnected")).toBe("Disconnected");
  });
});
