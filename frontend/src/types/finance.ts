export interface WatchlistItem {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: "up" | "down" | "flat";
}

export interface PositionRow {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

export interface PortfolioResponse {
  user_id: string;
  cash_balance: number;
  total_value: number;
  total_unrealized_pnl: number;
  positions: PositionRow[];
  timestamp: string;
}

export interface TradeAction {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
}

export interface WatchlistChange {
  ticker: string;
  action: "add" | "remove";
}

export interface ChatResponse {
  message: string;
  trades: TradeAction[];
  watchlist_changes: WatchlistChange[];
  executed_actions: { type: string; detail: string }[];
  errors: string[];
}
