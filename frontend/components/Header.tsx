import { ConnectionIndicator } from "@/components/ConnectionIndicator";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice } from "@/lib/format";
import type { ConnectionStatus } from "@/lib/types";

interface HeaderProps {
  status: ConnectionStatus;
  cash: number | null;
  totalValue: number | null;
}

export function Header({ status, cash, totalValue }: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-card p-6">
      <span className="text-heading text-primary">FinAlly</span>
      <div className="flex items-center gap-6">
        <div className="flex flex-col items-end gap-1">
          <span className="text-label text-muted-foreground">Cash</span>
          {cash == null ? (
            <Skeleton className="h-5 w-20" />
          ) : (
            <span className="text-body numeric text-foreground">{formatPrice(cash)}</span>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-label text-muted-foreground">Total Value</span>
          {totalValue == null ? (
            <Skeleton className="h-6 w-24" />
          ) : (
            <span className="text-display numeric text-foreground">
              {formatPrice(totalValue)}
            </span>
          )}
        </div>
        <ConnectionIndicator status={status} />
      </div>
    </header>
  );
}
