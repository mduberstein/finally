/**
 * Shared price/watchlist contract. Every later frontend plan (02-04) builds
 * against these names — do not rename them.
 */

export interface PriceTick {
  ticker: string;
  price: number;
  previous_price: number;
  change: number;
  change_percent: number;
  direction: "up" | "down" | "flat";
  timestamp: string;
}

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export interface WatchlistEntry {
  ticker: string;
  price: number | null;
  previous_price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: "up" | "down" | "flat" | null;
  timestamp: string | null;
}

export interface PositionEntry {
  ticker: string;
  quantity: number;
  avg_cost: number;
  price: number | null;
  unrealized_pnl: number | null;
  change_percent: number | null;
}

export interface PortfolioSnapshot {
  cash_balance: number;
  positions_value: number;
  total_value: number;
  positions: PositionEntry[];
}

export interface TradeResult {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  executed_at: string;
  cash_balance: number;
}
