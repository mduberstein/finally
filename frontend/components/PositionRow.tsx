import { formatPercent, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

interface PositionRowProps {
  ticker: string;
  quantity: number;
  avgCost: number;
  price: number | null;
  unrealizedPnl: number | null;
  changePercent: number | null;
}

/** Grid template shared with the column-header row so cells stay aligned. */
export const POSITION_ROW_GRID =
  "grid grid-cols-[1fr_80px_100px_100px_120px_100px] items-center gap-4";

/**
 * Color a P&L or percent-change cell with the up/down semantic tokens.
 * An exact zero or a null value stays in the default foreground color —
 * only a genuine gain or loss earns a color.
 */
function signColor(value: number | null): string {
  if (value == null || value === 0) return "text-foreground";
  if (value > 0) return "text-up";
  return "text-down";
}

export function PositionRow({
  ticker,
  quantity,
  avgCost,
  price,
  unrealizedPnl,
  changePercent,
}: PositionRowProps) {
  return (
    <div className={cn(POSITION_ROW_GRID, "px-4 py-3")}>
      <span className="text-label text-foreground">{ticker}</span>
      <span className="numeric text-body text-right text-foreground">{quantity}</span>
      <span className="numeric text-body text-right text-foreground">{formatPrice(avgCost)}</span>
      <span className="numeric text-display text-right text-foreground">{formatPrice(price)}</span>
      <span className={cn("numeric text-display text-right", signColor(unrealizedPnl))}>
        {formatPrice(unrealizedPnl)}
      </span>
      <span className={cn("numeric text-body text-right", signColor(changePercent))}>
        {formatPercent(changePercent)}
      </span>
    </div>
  );
}
