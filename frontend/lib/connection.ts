import type { ConnectionStatus } from "./types";

/** Consecutive EventSource error events after which status becomes "disconnected". */
export const DISCONNECTED_AFTER_ERRORS = 3;

/**
 * Milliseconds of silence since the last price event after which a
 * "connected" state is downgraded to "reconnecting", even if the underlying
 * EventSource still believes it is open. A native EventSource can sit in the
 * OPEN state against a wedged connection indefinitely, so trusting the
 * socket alone would paint the dot green over frozen prices. 10000ms is
 * twenty times the 500ms stream cadence, so normal jitter never trips it,
 * and the 15s server ping is not counted as a price event.
 */
export const STALE_AFTER_MS = 10000;

export interface ConnectionState {
  status: ConnectionStatus;
  consecutiveErrors: number;
  lastMessageAt: number;
}

export type ConnectionEvent =
  | { kind: "open" }
  | { kind: "message" }
  | { kind: "error" }
  | { kind: "tick" };

/** The stream is not yet proven healthy on first mount. */
export function initialConnectionState(now: number): ConnectionState {
  return { status: "reconnecting", consecutiveErrors: 0, lastMessageAt: now };
}

/**
 * Pure reducer over EventSource-derived events plus a clock tick. Time is
 * always injected via `now`, never read inside this module, so retry
 * escalation and staleness behavior are testable without fake timers.
 */
export function reduceConnection(
  state: ConnectionState,
  event: ConnectionEvent,
  now: number,
): ConnectionState {
  switch (event.kind) {
    case "open":
      return { status: "connected", consecutiveErrors: 0, lastMessageAt: state.lastMessageAt };
    case "message":
      return { status: "connected", consecutiveErrors: 0, lastMessageAt: now };
    case "error": {
      const consecutiveErrors = state.consecutiveErrors + 1;
      const status: ConnectionStatus =
        consecutiveErrors >= DISCONNECTED_AFTER_ERRORS ? "disconnected" : "reconnecting";
      return { status, consecutiveErrors, lastMessageAt: state.lastMessageAt };
    }
    case "tick": {
      if (state.status !== "connected") return state;
      const isStale = now - state.lastMessageAt >= STALE_AFTER_MS;
      return isStale ? { ...state, status: "reconnecting" } : state;
    }
  }
}

/** The three fixed label strings shown for each connection status. */
export function statusLabel(status: ConnectionStatus): string {
  switch (status) {
    case "connected":
      return "Connected";
    case "reconnecting":
      return "Reconnecting";
    case "disconnected":
      return "Disconnected";
  }
}
