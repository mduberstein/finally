"use client";

import { useEffect, useState } from "react";

import {
  directionGlyph,
  FLASH_DURATION_MS,
  isFlashActive,
  nextFlashState,
  type FlashState,
} from "@/lib/flash";
import { formatPercent, formatPrice } from "@/lib/format";
import type { PriceTick } from "@/lib/types";
import { cn } from "@/lib/utils";

interface PriceCellProps {
  price: number | null;
  changePercent: number | null;
  direction: PriceTick["direction"] | null;
}

/**
 * The price and percent-change cells for one watchlist row. The price cell
 * flashes green/red on a tick and fades over `FLASH_DURATION_MS`; the
 * direction glyph and signed percent are the non-color channel and always
 * render, flash or not.
 */
export function PriceCell({ price, changePercent, direction }: PriceCellProps) {
  const [flash, setFlash] = useState<FlashState | null>(null);

  // A new tick is any render where direction/price actually moved — a flat
  // tick repeats the same price, so it never re-enters this effect, which
  // matches nextFlashState's own flat no-op. Reading wall-clock time is an
  // external side effect, so it belongs in an effect rather than render.
  useEffect(() => {
    if (direction == null) return;
    const tick = { direction } as PriceTick;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- synchronizes with wall-clock time, an external source, not derived from props alone
    setFlash((prev) => nextFlashState(prev, tick, Date.now()));
  }, [direction, price]);

  // Clear the flash once its window elapses so a ticker that stops moving
  // does not keep a stale tint applied.
  useEffect(() => {
    if (flash == null) return;
    const timer = window.setTimeout(() => {
      setFlash((prev) => (prev != null && !isFlashActive(prev, Date.now()) ? null : prev));
    }, FLASH_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, [flash]);

  const animationClass =
    flash == null ? "" : flash.direction === "up" ? "animate-flash-up" : "animate-flash-down";

  return (
    <>
      {/* Keying on startedAt remounts this node on every new flash, which is
          what restarts the CSS animation from full intensity instead of the
          already-running animation swallowing a rapid second tick. */}
      <span
        key={flash?.startedAt ?? "idle"}
        className={cn("numeric text-display text-right text-foreground", animationClass)}
      >
        {formatPrice(price)}
      </span>
      <span className="text-body flex items-center justify-end gap-1 text-muted-foreground">
        <span aria-hidden="true">{direction ? directionGlyph(direction) : ""}</span>
        <span className="numeric">{formatPercent(changePercent)}</span>
      </span>
    </>
  );
}
