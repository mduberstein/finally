import { statusLabel } from "@/lib/connection";
import type { ConnectionStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const DOT_COLOR: Record<ConnectionStatus, string> = {
  connected: "bg-up",
  reconnecting: "bg-reconnecting",
  disconnected: "bg-down",
};

/**
 * UI-SPEC Copywriting Contract error sentence — carried as the accessible
 * description while disconnected, not as the visible label. The visible
 * label stays the fixed three-string enum (`statusLabel`) so the header
 * never needs overflow handling; this longer sentence is exposed to
 * assistive technology only, satisfying both the fixed-label rule and the
 * "no separate error banner" rule.
 */
const DISCONNECTED_DESCRIPTION = "Live prices unavailable — reconnecting automatically.";

interface ConnectionIndicatorProps {
  status: ConnectionStatus;
}

/** Header dot and label reflecting stream health — the sole error surface for the price feed. */
export function ConnectionIndicator({ status }: ConnectionIndicatorProps) {
  const describedBy = status === "disconnected" ? "connection-status-description" : undefined;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-describedby={describedBy}
      className="flex items-center gap-1"
    >
      <span className={cn("h-2 w-2 rounded-full", DOT_COLOR[status])} aria-hidden="true" />
      <span className="text-label text-foreground">{statusLabel(status)}</span>
      {status === "disconnected" && (
        <span id="connection-status-description" className="sr-only">
          {DISCONNECTED_DESCRIPTION}
        </span>
      )}
    </div>
  );
}
