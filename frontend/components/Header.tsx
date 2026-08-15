import { ConnectionIndicator } from "@/components/ConnectionIndicator";
import type { ConnectionStatus } from "@/lib/types";

interface HeaderProps {
  status: ConnectionStatus;
}

export function Header({ status }: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-card p-6">
      <span className="text-heading text-primary">FinAlly</span>
      <ConnectionIndicator status={status} />
    </header>
  );
}
