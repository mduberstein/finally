import { act } from "@testing-library/react";
import { priceStore } from "@/lib/priceStore";
import type { Direction, PriceTick } from "@/lib/types";

/** Stand-in for the browser EventSource, driven by the test. */
export class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  static last: FakeEventSource | null = null;

  readyState = FakeEventSource.CONNECTING;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;

  private listeners: ((event: MessageEvent) => void)[] = [];

  constructor(readonly url: string) {
    FakeEventSource.last = this;
  }

  addEventListener(_type: string, listener: (event: MessageEvent) => void) {
    this.listeners.push(listener);
  }

  dispatch(data: string) {
    this.listeners.forEach((listener) => listener({ data } as MessageEvent));
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
}

function installFake() {
  (globalThis as unknown as { EventSource: unknown }).EventSource = FakeEventSource;
}

/** Connects the shared store to a fake stream and marks it open. */
export function startStream(): FakeEventSource {
  installFake();
  priceStore.connect();
  const source = FakeEventSource.last!;
  act(() => {
    source.readyState = FakeEventSource.OPEN;
    source.onopen?.();
  });
  return source;
}

export function stopStream() {
  priceStore.reset();
}

/** Raises an EventSource error in the given readyState. */
export function failStream(readyState: number) {
  const source = FakeEventSource.last;
  if (!source) throw new Error("startStream() must run first");
  act(() => {
    source.readyState = readyState;
    source.onerror?.();
  });
}

export function makeTick(
  ticker: string,
  price: number,
  direction: Direction = "up",
  previous = price,
): PriceTick {
  return {
    ticker,
    price,
    previous_price: previous,
    change: price - previous,
    change_percent: previous === 0 ? 0 : ((price - previous) / previous) * 100,
    direction,
    timestamp: new Date(Date.now()).toISOString(),
  };
}

/** Pushes a tick through the store the way the server would. */
export function emit(tick: PriceTick) {
  const source = FakeEventSource.last;
  if (!source) throw new Error("startStream() must run first");
  act(() => {
    source.dispatch(JSON.stringify(tick));
  });
}
