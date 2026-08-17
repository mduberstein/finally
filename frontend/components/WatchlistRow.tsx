import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PriceCell } from "@/components/PriceCell";
import { Sparkline } from "@/components/Sparkline";
import type { PricePoint } from "@/lib/priceHistory";
import type { PriceTick } from "@/lib/types";
import { cn } from "@/lib/utils";

interface WatchlistRowProps {
  ticker: string;
  price?: number | null;
  changePercent?: number | null;
  direction?: PriceTick["direction"] | null;
  points?: PricePoint[];
  selected?: boolean;
  onSelect?: () => void;
  onRemove?: () => void;
  removing?: boolean;
}

/** Grid template shared with the column-header row so cells stay aligned:
 * ticker, price, percent, sparkline, and the remove-control slot. */
export const WATCHLIST_ROW_GRID =
  "grid grid-cols-[minmax(48px,1fr)_88px_72px_96px_28px] items-center gap-2";

export function WatchlistRow({
  ticker,
  price,
  changePercent,
  direction = null,
  points = [],
  selected = false,
  onSelect,
  onRemove,
  removing = false,
}: WatchlistRowProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect?.();
        }
      }}
      className={cn(
        WATCHLIST_ROW_GRID,
        "cursor-pointer border-l-2 px-4 py-3 outline-none transition-colors",
        "hover:border-l-primary focus-visible:border-l-primary focus-visible:ring-2 focus-visible:ring-ring",
        selected ? "border-l-primary bg-accent/40" : "border-l-transparent",
      )}
    >
      <span className="text-label text-foreground">{ticker}</span>
      <PriceCell price={price ?? null} changePercent={changePercent ?? null} direction={direction} />
      <Sparkline points={points} />
      <Button
        variant="ghost"
        size="icon"
        disabled={removing}
        aria-label={`Remove ${ticker} from watchlist`}
        onClick={(event) => {
          event.stopPropagation();
          onRemove?.();
        }}
        className="text-muted-foreground hover:text-foreground"
      >
        <X size={14} />
      </Button>
    </div>
  );
}
