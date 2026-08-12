"use client";

import { Panel } from "./Panel";
import { money, quantity, signedMoney, signedPercent, toneClass } from "@/lib/format";
import { useTick } from "@/lib/priceStore";
import { useFlash } from "@/lib/useFlash";
import type { Position } from "@/lib/types";

const ROW = "grid grid-cols-[3.4rem_repeat(6,1fr)] items-center gap-2 px-2";

interface PositionsTableProps {
  positions: Position[];
  selected: string | null;
  onSelect: (ticker: string) => void;
}

export function PositionsTable({ positions, selected, onSelect }: PositionsTableProps) {
  return (
    <Panel
      title="Positions"
      testId="positions-table"
      aside={<span className="text-ink-faint">{positions.length}</span>}
    >
      <div className={`${ROW} label h-6 border-b border-line-soft`}>
        <span>Sym</span>
        <span className="text-right">Qty</span>
        <span className="text-right">Avg cost</span>
        <span className="text-right">Last</span>
        <span className="text-right">Value</span>
        <span className="text-right">Unrealized</span>
        <span className="text-right">%</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {positions.length === 0 ? (
          <p data-testid="positions-empty" className="px-2 py-3 text-ink-faint">
            No open positions. Use the ticket below to buy.
          </p>
        ) : (
          positions.map((position) => (
            <PositionRow
              key={position.ticker}
              position={position}
              selected={position.ticker === selected}
              onSelect={onSelect}
            />
          ))
        )}
      </div>
    </Panel>
  );
}

interface RowProps {
  position: Position;
  selected: boolean;
  onSelect: (ticker: string) => void;
}

function PositionRow({ position, selected, onSelect }: RowProps) {
  const tick = useTick(position.ticker);
  const flashRef = useFlash<HTMLSpanElement>(position.ticker);
  const price = tick?.price ?? position.current_price;
  const marketValue = price * position.quantity;
  const cost = position.avg_cost * position.quantity;
  const pnl = marketValue - cost;
  const pnlPercent = cost === 0 ? 0 : (pnl / cost) * 100;

  return (
    <div
      data-testid={`position-row-${position.ticker}`}
      role="button"
      tabIndex={0}
      onClick={() => onSelect(position.ticker)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(position.ticker);
        }
      }}
      className={`${ROW} h-7 cursor-pointer border-b border-line-soft/60 hover:bg-raise/60 ${
        selected ? "rail bg-raise" : ""
      }`}
    >
      <span className={selected ? "text-accent" : "text-ink"}>{position.ticker}</span>
      <span className="text-right text-ink-dim">{quantity(position.quantity)}</span>
      <span className="text-right text-ink-dim">{money(position.avg_cost)}</span>
      <span className="text-right text-ink">
        <span
          ref={flashRef}
          data-testid={`position-price-${position.ticker}`}
          className="flashable inline-block rounded-xs px-1"
        >
          {money(price)}
        </span>
      </span>
      <span className="text-right text-ink">{money(marketValue)}</span>
      <span data-testid={`position-pnl-${position.ticker}`} className={`text-right ${toneClass(pnl)}`}>
        {signedMoney(pnl)}
      </span>
      <span className={`text-right ${toneClass(pnl)}`}>{signedPercent(pnlPercent)}</span>
    </div>
  );
}
