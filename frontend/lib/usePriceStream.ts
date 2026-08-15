"use client";

import { useEffect, useState } from "react";

import { initialConnectionState, reduceConnection } from "./connection";
import type { ConnectionStatus, PriceTick } from "./types";

interface PriceStreamState {
  prices: Record<string, PriceTick>;
  status: ConnectionStatus;
}

/** How often a "tick" event is dispatched to catch a wedged-but-open connection. */
const TICK_INTERVAL_MS = 2000;

/**
 * Live prices from the `/api/stream/prices` SSE endpoint, merged by ticker.
 *
 * A ticker that hasn't ticked recently keeps its last known price — new
 * frames are merged into state, never replacing the whole map. `status`
 * comes from the three-state connection reducer in `./connection`, fed by
 * the EventSource's own open/message/error events plus a periodic clock
 * tick so a stream that stops sending prices while the socket still
 * believes it's open is still reported honestly.
 *
 * Reconnection is left entirely to the native `EventSource`, which already
 * retries on its own — no hand-rolled retry loop is added on top.
 */
export function usePriceStream(): PriceStreamState {
  const [prices, setPrices] = useState<Record<string, PriceTick>>({});
  const [connection, setConnection] = useState(() => initialConnectionState(Date.now()));

  useEffect(() => {
    const source = new EventSource("/api/stream/prices");

    source.onopen = () => setConnection((state) => reduceConnection(state, { kind: "open" }, Date.now()));
    source.onerror = () => setConnection((state) => reduceConnection(state, { kind: "error" }, Date.now()));

    source.addEventListener("price", (event: MessageEvent<string>) => {
      const tick = JSON.parse(event.data) as PriceTick;
      setPrices((current) => ({ ...current, [tick.ticker]: tick }));
      setConnection((state) => reduceConnection(state, { kind: "message" }, Date.now()));
    });

    const tickIntervalId = setInterval(() => {
      setConnection((state) => reduceConnection(state, { kind: "tick" }, Date.now()));
    }, TICK_INTERVAL_MS);

    return () => {
      clearInterval(tickIntervalId);
      source.close();
    };
  }, []);

  return { prices, status: connection.status };
}
