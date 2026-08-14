"use client";

import { useEffect, useState } from "react";
import type { ConnectionStatus, PriceTick } from "./types";

interface PriceStreamState {
  prices: Record<string, PriceTick>;
  status: ConnectionStatus;
}

/**
 * Live prices from the `/api/stream/prices` SSE endpoint, merged by ticker.
 *
 * A ticker that hasn't ticked recently keeps its last known price — new
 * frames are merged into state, never replacing the whole map. `status` is
 * a simple two-state signal for now ("connected" on open, "reconnecting" on
 * error); Plan 04 replaces this with the full three-state machine, which is
 * why `status` is part of the return shape from the start.
 */
export function usePriceStream(): PriceStreamState {
  const [prices, setPrices] = useState<Record<string, PriceTick>>({});
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");

  useEffect(() => {
    const source = new EventSource("/api/stream/prices");

    source.onopen = () => setStatus("connected");
    source.onerror = () => setStatus("reconnecting");

    source.addEventListener("price", (event: MessageEvent<string>) => {
      const tick = JSON.parse(event.data) as PriceTick;
      setPrices((current) => ({ ...current, [tick.ticker]: tick }));
    });

    return () => source.close();
  }, []);

  return { prices, status };
}
