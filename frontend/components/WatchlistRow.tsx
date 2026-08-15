import { formatPercent, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

interface WatchlistRowProps {
  ticker: string;
  price?: number | null;
  changePercent?: number | null;
  selected?: boolean;
  onSelect?: () => void;
}

/** Grid template shared with the column-header row so cells stay aligned. */
export const WATCHLIST_ROW_GRID = "grid grid-cols-[1fr_120px_100px] items-center gap-4";

export function WatchlistRow({
  ticker,
  price,
  changePercent,
  selected = false,
  onSelect,
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
      <span className="numeric text-display text-right text-foreground">{formatPrice(price)}</span>
      <span className="numeric text-body text-right text-muted-foreground">
        {formatPercent(changePercent)}
      </span>
    </div>
  );
}
