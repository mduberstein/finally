"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Panel } from "./Panel";
import { signedPercent } from "@/lib/format";
import { priceStore, usePriceVersion } from "@/lib/priceStore";
import { squarify } from "@/lib/treemap";
import type { Position } from "@/lib/types";

/** P&L beyond this magnitude saturates the tile color. */
const SATURATION_PERCENT = 5;

function tileColor(pnlPercent: number): string {
  const magnitude = Math.min(Math.abs(pnlPercent) / SATURATION_PERCENT, 1);
  const mix = 14 + magnitude * 56;
  const hue = pnlPercent >= 0 ? "#21c07a" : "#f0576b";
  return `color-mix(in srgb, ${hue} ${mix.toFixed(0)}%, #101620)`;
}

/** Live P&L for a position, marked to the price cache. */
function livePnlPercent(position: Position): number {
  const price = priceStore.getPrice(position.ticker) ?? position.current_price;
  const cost = position.avg_cost * position.quantity;
  if (cost === 0) return 0;
  return ((price * position.quantity - cost) / cost) * 100;
}

interface HeatmapProps {
  positions: Position[];
  selected: string | null;
  onSelect: (ticker: string) => void;
}

/** Positions sized by portfolio weight, colored by unrealized P&L. */
export function Heatmap({ positions, selected, onSelect }: HeatmapProps) {
  usePriceVersion();
  const containerRef = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const element = containerRef.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      setBox({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const rects = useMemo(
    () => squarify(positions.map((position) => position.weight), box.width, box.height),
    [positions, box.width, box.height],
  );

  return (
    <Panel title="Allocation" testId="heatmap">
      <div ref={containerRef} className="relative min-h-0 flex-1">
        {positions.length === 0 ? (
          <p
            data-testid="heatmap-empty"
            className="absolute inset-0 flex items-center justify-center px-3 text-center text-ink-faint"
          >
            No positions. Buy something to fill the map.
          </p>
        ) : (
          positions.map((position, index) => {
            const rect = rects[index];
            const pnl = livePnlPercent(position);
            const roomy = rect.width > 54 && rect.height > 30;
            return (
              <button
                key={position.ticker}
                data-testid={`heatmap-tile-${position.ticker}`}
                onClick={() => onSelect(position.ticker)}
                title={`${position.ticker} ${signedPercent(pnl)}`}
                style={{
                  left: rect.x,
                  top: rect.y,
                  width: Math.max(rect.width - 1, 0),
                  height: Math.max(rect.height - 1, 0),
                  background: tileColor(pnl),
                }}
                className={`absolute flex flex-col items-start justify-center overflow-hidden px-1.5 text-left transition-[box-shadow] ${
                  position.ticker === selected ? "rail" : ""
                }`}
              >
                <span className="text-ink">{position.ticker}</span>
                {roomy ? (
                  <span className="text-micro text-ink-dim">{signedPercent(pnl)}</span>
                ) : null}
              </button>
            );
          })
        )}
      </div>
    </Panel>
  );
}
