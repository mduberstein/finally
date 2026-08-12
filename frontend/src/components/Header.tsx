"use client";

import { useEffect, useState } from "react";
import { money, signedMoney, signedPercent, toneClass } from "@/lib/format";
import { priceStore, useConnectionStatus, usePriceVersion } from "@/lib/priceStore";
import type { Portfolio } from "@/lib/types";

const STATUS_TEXT = {
  connected: "Live",
  reconnecting: "Reconnecting",
  disconnected: "Offline",
} as const;

const STATUS_DOT = {
  connected: "bg-up",
  reconnecting: "bg-accent",
  disconnected: "bg-down",
} as const;

/** Positions marked to the live cache, so the header moves with the tape. */
function liveTotals(portfolio: Portfolio) {
  const positionsValue = portfolio.positions.reduce((total, position) => {
    const price = priceStore.getPrice(position.ticker) ?? position.current_price;
    return total + position.quantity * price;
  }, 0);
  const cost = portfolio.positions.reduce(
    (total, position) => total + position.quantity * position.avg_cost,
    0,
  );
  const pnl = positionsValue - cost;
  return {
    totalValue: portfolio.cash_balance + positionsValue,
    pnl,
    pnlPercent: cost === 0 ? 0 : (pnl / cost) * 100,
  };
}

export function Header({ portfolio }: { portfolio: Portfolio | null }) {
  usePriceVersion();
  const status = useConnectionStatus();
  const totals = portfolio ? liveTotals(portfolio) : null;

  return (
    <header
      data-testid="header"
      className="flex h-12 shrink-0 items-stretch gap-px bg-void"
    >
      <div className="flex items-center gap-2 bg-panel px-3">
        <span className="font-sans text-figure font-semibold tracking-[0.18em] text-ink">
          FIN<span className="text-accent">ALLY</span>
        </span>
        <span className="label hidden sm:inline">Terminal</span>
      </div>

      <Stat label="Total value" testId="header-total-value" wide>
        <span className="text-hero text-ink">{money(totals?.totalValue ?? null)}</span>
      </Stat>

      <Stat label="Unrealized P&L" testId="header-pnl">
        <span className={`text-figure ${toneClass(totals?.pnl ?? null)}`}>
          {signedMoney(totals?.pnl ?? null)}
          <span className="ml-2 text-data">{signedPercent(totals?.pnlPercent ?? null)}</span>
        </span>
      </Stat>

      <Stat label="Cash" testId="header-cash">
        <span className="text-figure text-ink">{money(portfolio?.cash_balance ?? null)}</span>
      </Stat>

      <div className="flex flex-1 items-center justify-end gap-4 bg-panel px-3">
        <Clock />
        <span
          data-testid="connection-status"
          data-status={status}
          className="flex items-center gap-2"
        >
          <span aria-hidden className={`h-2 w-2 rounded-full ${STATUS_DOT[status]}`} />
          <span className="label">{STATUS_TEXT[status]}</span>
        </span>
      </div>
    </header>
  );
}

/** UTC session clock. Renders blank until mounted so hydration stays stable. */
function Clock() {
  const [now, setNow] = useState<string | null>(null);

  useEffect(() => {
    const tick = () =>
      setNow(
        new Date().toLocaleTimeString("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          timeZone: "UTC",
        }),
      );
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <span className="hidden items-baseline gap-1.5 lg:flex">
      <span className="text-ink-dim">{now ?? "--:--:--"}</span>
      <span className="label">UTC</span>
    </span>
  );
}

interface StatProps {
  label: string;
  testId: string;
  wide?: boolean;
  children: React.ReactNode;
}

function Stat({ label, testId, wide, children }: StatProps) {
  return (
    <div
      className={`flex-col justify-center bg-panel px-3 ${
        wide ? "flex min-w-[9rem]" : "hidden md:flex"
      }`}
    >
      <span className="label leading-none">{label}</span>
      <span data-testid={testId} className="mt-1 leading-none">
        {children}
      </span>
    </div>
  );
}
