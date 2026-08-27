"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import type { ChatResponse, PortfolioResponse, WatchlistItem } from "../types/finance";
import { computeSparkline, formatCurrency, toTwo } from "../lib/utils";

type PriceMap = Record<string, WatchlistItem>;
type ChartDataMap = Record<string, { t: number; p: number }[]>;
type MessageItem = { role: "user" | "assistant"; text: string; details?: string[] };
type FlashMap = Record<string, "up" | "down" | "">;
type ConnectionState = "connected" | "reconnecting" | "disconnected";

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) {
    return <span className="text-xs text-zinc-500">—</span>;
  }
  const d = computeSparkline(points);
  return (
    <svg width={160} height={30} viewBox="0 0 140 28" className="text-emerald-300">
      <path d={d} fill="none" stroke="currentColor" strokeWidth={1.2} />
    </svg>
  );
}

const createEmptyPortfolio = (): PortfolioResponse => ({
  user_id: "default",
  cash_balance: 10000,
  total_value: 10000,
  total_unrealized_pnl: 0,
  positions: [],
  timestamp: "",
});

export default function FinAllyPage() {
  const [portfolio, setPortfolio] = useState<PortfolioResponse>(createEmptyPortfolio());
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [prices, setPrices] = useState<PriceMap>({});
  const [flash, setFlash] = useState<FlashMap>({});
  const [selectedTicker, setSelectedTicker] = useState("AAPL");
  const [connection, setConnection] = useState<ConnectionState>("disconnected");
  const [statusMessage, setStatusMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [tradeTicker, setTradeTicker] = useState("AAPL");
  const [tradeQty, setTradeQty] = useState("1");
  const [chatMessage, setChatMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<MessageItem[]>([
    { role: "assistant", text: "Welcome to FinAlly. Ask me to trade or adjust watchlists." },
  ]);
  const [history, setHistory] = useState<{ recorded_at: string; total_value: number }[]>([]);
  const [priceHistory, setPriceHistory] = useState<ChartDataMap>({});
  const [newTicker, setNewTicker] = useState("");

  const selectedPosition = portfolio.positions.find((position) => position.ticker === selectedTicker);
  const selectedHistory = priceHistory[selectedTicker] ?? [];
  const pnlHistory = history.map((point) => ({ t: point.recorded_at, value: point.total_value }));
  const currentTickers = useMemo(() => new Set(watchlist.map((item) => item.ticker)), [watchlist]);

  const heatmapScale = useMemo(() => {
    const total = portfolio.positions.reduce((sum, position) => sum + Math.abs(position.quantity * position.current_price), 0);
    return portfolio.positions.map((position) => ({
      ...position,
      weight: total === 0 ? 0 : Math.abs(position.quantity * position.current_price) / total,
    }));
  }, [portfolio.positions]);

  const watchlistRows = useMemo(
    () =>
      watchlist.map((item) => {
        const live = prices[item.ticker];
        return live ?? { ...item, price: 0, previous_price: 0, timestamp: 0, change: 0, change_percent: 0, direction: "flat" };
      }),
    [watchlist, prices]
  );

  const refreshWatchlist = useCallback(async () => {
    const watchlistData = await api.getWatchlist();
    const seededPrices = Object.fromEntries(watchlistData.map((item) => [item.ticker, item]));
    setWatchlist(watchlistData);
    setPrices((prev) => ({ ...prev, ...seededPrices }));
    if (!currentTickers.size && watchlistData[0]) {
      setSelectedTicker(watchlistData[0].ticker);
      setTradeTicker(watchlistData[0].ticker);
    }
  }, [currentTickers]);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const [portfolioData, historyData] = await Promise.all([api.getPortfolio(), api.getPortfolioHistory()]);
        setPortfolio(portfolioData);
        setHistory(historyData);
        await refreshWatchlist();
      } catch (error) {
        setStatusMessage((error as Error).message);
      }
    };
    void bootstrap();
  }, [refreshWatchlist]);

  useEffect(() => {
    const source = new EventSource("/api/stream/prices");

    source.onopen = () => setConnection("connected");
    source.onerror = () => setConnection("reconnecting");

    source.onmessage = (event) => {
      try {
        const incoming = JSON.parse(event.data) as Record<string, WatchlistItem>;
        setPrices((prev) => {
          const next = { ...prev };
          for (const [ticker, item] of Object.entries(incoming)) {
            const previous = next[ticker];
            if (!previous) {
              setFlash((old) => ({ ...old, [ticker]: "" }));
            } else if (item.price > previous.price) {
              setFlash((old) => ({ ...old, [ticker]: "up" }));
            } else if (item.price < previous.price) {
              setFlash((old) => ({ ...old, [ticker]: "down" }));
            }
            setTimeout(() => {
              setFlash((old) => ({ ...old, [ticker]: "" }));
            }, 500);
            next[ticker] = item;
          }
          return next;
        });

        setPriceHistory((prev) => {
          const next = { ...prev };
            for (const [ticker, item] of Object.entries(incoming)) {
              const updated = [...(next[ticker] ?? []), { t: item.timestamp * 1000, p: item.price }].slice(-140);
              next[ticker] = updated;
            }
            return next;
        });
      } catch {
        setStatusMessage("Malformed SSE payload");
      }
    };

    source.addEventListener("error", () => {
      if (source.readyState === EventSource.CLOSED) {
        setConnection("disconnected");
      }
    });

    return () => {
      source.close();
      setConnection("disconnected");
    };
  }, []);

  const handleTrade = async (side: "buy" | "sell") => {
    if (Number.isNaN(Number(tradeQty)) || Number(tradeQty) <= 0) {
      setStatusMessage("Trade quantity must be greater than zero.");
      return;
    }
    setLoading(true);
    setStatusMessage("");
    try {
      const payload = await api.executeTrade(tradeTicker, side, Number(tradeQty));
      setPortfolio(payload.portfolio);
      setTradeQty("1");
      setChatMessages((prev) => [...prev, { role: "assistant", text: `Executed ${side} ${tradeQty} ${tradeTicker}` }]);
      void api.getPortfolioHistory().then(setHistory);
    } catch (error) {
      setStatusMessage((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const sendChat = async () => {
    if (!chatMessage.trim()) return;
    setChatLoading(true);
    setChatMessages((prev) => [...prev, { role: "user", text: chatMessage }]);
    try {
      const response: ChatResponse = await api.postChat(chatMessage);
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: response.message,
          details: response.executed_actions.map((action) => action.detail),
        },
      ]);
      const [refreshedPortfolio, refreshedHistory] = await Promise.all([api.getPortfolio(), api.getPortfolioHistory()]);
      setPortfolio(refreshedPortfolio);
      setHistory(refreshedHistory);
      await refreshWatchlist();
      setStatusMessage("");
    } catch (error) {
      setChatMessages((prev) => [...prev, { role: "assistant", text: (error as Error).message || "Chat failed" }]);
    } finally {
      setChatLoading(false);
      setChatMessage("");
    }
  };

  const addWatchlist = async () => {
    if (!newTicker.trim()) return;
    setStatusMessage("");
    await api.addWatchlist(newTicker);
    setNewTicker("");
    await refreshWatchlist();
  };

  const removeWatchlist = async (ticker: string) => {
    await api.removeWatchlist(ticker);
    setWatchlist((prev) => prev.filter((item) => item.ticker !== ticker));
    setPrices((prev) => {
      const next = { ...prev };
      delete next[ticker];
      return next;
    });
    setPriceHistory((prev) => {
      const next = { ...prev };
      delete next[ticker];
      return next;
    });
    if (selectedTicker === ticker) {
      const fallback = watchlist.find((item) => item.ticker !== ticker);
      if (fallback) {
        setSelectedTicker(fallback.ticker);
        setTradeTicker(fallback.ticker);
      }
    }
    if (tradeTicker === ticker) {
      setTradeTicker(watchlist.find((item) => item.ticker !== ticker)?.ticker ?? "AAPL");
    }
  };

  return (
    <div className="min-h-screen p-4 bg-[var(--bg)] text-[var(--text)]">
      <header className="mb-3 rounded-md border border-zinc-700 bg-[var(--panel)] p-4 flex flex-wrap items-center gap-6">
        <h1 className="text-xl font-semibold tracking-tight text-white">FinAlly</h1>
        <div className="text-sm">
          Cash: <span className="font-semibold">{formatCurrency(portfolio.cash_balance)}</span>
        </div>
        <div className="text-sm">
          Total Value: <span className="font-semibold">{formatCurrency(portfolio.total_value)}</span>
        </div>
        <div className="text-sm">
          P&L: <span className={portfolio.total_unrealized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}>{formatCurrency(portfolio.total_unrealized_pnl)}</span>
        </div>
        <span
          className={`inline-flex h-2.5 w-2.5 rounded-full ${
            connection === "connected" ? "bg-emerald-500" : connection === "reconnecting" ? "bg-amber-500" : "bg-red-500"
          }`}
          title={`Stream ${connection}`}
        />
      </header>

      {statusMessage && <p className="mb-3 rounded border border-zinc-700 bg-zinc-800/70 p-2 text-xs text-rose-300">{statusMessage}</p>}

      <main className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <section className="rounded-md border border-zinc-700 bg-[var(--panel)] p-3">
              <h2 className="mb-2 text-sm font-semibold">Watchlist</h2>
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <input
                  className="rounded border border-zinc-600 bg-black/25 px-2 py-1 text-xs"
                  value={newTicker}
                  onChange={(event) => setNewTicker(event.target.value.toUpperCase())}
                  placeholder="ADD TICKER"
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      void addWatchlist();
                    }
                  }}
                />
                <button className="rounded border border-zinc-600 px-3 py-1 text-xs hover:bg-zinc-600/50" onClick={() => void addWatchlist()}>
                  Add
                </button>
              </div>
              <table className="mt-2 w-full text-xs">
                <thead>
                  <tr className="text-left text-zinc-400">
                    <th className="py-1">Ticker</th>
                    <th className="py-1">Price</th>
                    <th className="py-1">Change %</th>
                    <th className="py-1">Spark</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {watchlistRows.map((item) => (
                    <tr
                      key={item.ticker}
                      className={`cursor-pointer border-t border-zinc-700 ${flash[item.ticker] ? `flash-${flash[item.ticker]}` : ""}`}
                      onClick={() => {
                        setSelectedTicker(item.ticker);
                        setTradeTicker(item.ticker);
                      }}
                    >
                      <td className="py-1">{item.ticker}</td>
                      <td className="py-1">{formatCurrency(item.price)}</td>
                      <td className={`py-1 ${item.direction === "up" ? "text-emerald-400" : item.direction === "down" ? "text-rose-400" : ""}`}>
                        {toTwo(item.change_percent)}%
                      </td>
                      <td className="py-1">
                        <Sparkline
                          points={(priceHistory[item.ticker] ?? []).map((point) => point.p)}
                        />
                      </td>
                      <td className="py-1">
                        <button
                          className="rounded border border-zinc-600 px-2 py-1 text-[10px] hover:bg-zinc-600/50"
                          onClick={(event) => {
                            event.stopPropagation();
                            void removeWatchlist(item.ticker);
                          }}
                        >
                          remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="rounded-md border border-zinc-700 bg-[var(--panel)] p-3">
              <h2 className="mb-2 text-sm font-semibold">Main Chart - {selectedTicker}</h2>
              {selectedHistory.length > 1 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={selectedHistory}>
                    <XAxis dataKey="t" hide />
                    <YAxis domain={["auto", "auto"]} />
                    <Tooltip
                      labelFormatter={(value) => new Date(Number(value)).toLocaleTimeString()}
                      formatter={(value: number) => [formatCurrency(value), selectedTicker]}
                    />
                    <Line type="monotone" dataKey="p" stroke="#209dd7" dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-xs text-zinc-500">Waiting for stream updates.</p>
              )}
              {selectedPosition && (
                <div className="mt-2 text-xs text-zinc-300">
                  Current Position: {selectedPosition.quantity.toFixed(3)} @ {formatCurrency(selectedPosition.avg_cost)} | Market{" "}
                  {formatCurrency(selectedPosition.current_price)} | Unrealized {formatCurrency(selectedPosition.unrealized_pnl)}
                </div>
              )}
            </section>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <section className="rounded-md border border-zinc-700 bg-[var(--panel)] p-3">
              <h2 className="mb-2 text-sm font-semibold">Trade</h2>
              <div className="flex gap-2 text-xs">
                <input
                  className="w-24 rounded border border-zinc-600 bg-black/25 px-2 py-1"
                  value={tradeTicker}
                  onChange={(event) => setTradeTicker(event.target.value.toUpperCase())}
                />
                <input
                  className="w-20 rounded border border-zinc-600 bg-black/25 px-2 py-1"
                  value={tradeQty}
                  onChange={(event) => setTradeQty(event.target.value)}
                  inputMode="decimal"
                />
                <button
                  className="rounded bg-blue-700 px-3 py-1 font-semibold"
                  onClick={() => void handleTrade("buy")}
                  disabled={loading}
                >
                  Buy
                </button>
                <button
                  className="rounded bg-purple-700 px-3 py-1 font-semibold"
                  onClick={() => void handleTrade("sell")}
                  disabled={loading}
                >
                  Sell
                </button>
              </div>
            </section>

            <section className="rounded-md border border-zinc-700 bg-[var(--panel)] p-3">
              <h2 className="mb-2 text-sm font-semibold">Portfolio Heatmap</h2>
              <div className="grid grid-cols-2 gap-2">
                {heatmapScale.map((position) => (
                  <div
                    key={position.ticker}
                    className={`rounded border border-zinc-600 p-2 ${position.unrealized_pnl >= 0 ? "bg-emerald-950/40" : "bg-rose-950/50"}`}
                    style={{ minHeight: 64 }}
                  >
                    <p className="text-xs font-semibold">{position.ticker}</p>
                    <p className="text-[11px] text-zinc-300">{toTwo(position.weight * 100)}%</p>
                    <p className="text-xs">{formatCurrency(position.unrealized_pnl)}</p>
                  </div>
                ))}
                {heatmapScale.length === 0 && <p className="text-xs text-zinc-400">No open positions.</p>}
              </div>
            </section>
          </div>

          <section className="rounded-md border border-zinc-700 bg-[var(--panel)] p-3">
            <h2 className="mb-2 text-sm font-semibold">P&L Chart</h2>
            {pnlHistory.length > 1 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={pnlHistory}>
                  <XAxis dataKey="t" hide />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" stroke="#ecad0a" dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-xs text-zinc-500">No snapshots yet.</p>
            )}
          </section>
        </section>

        <section className="space-y-4">
          <section className="rounded-md border border-zinc-700 bg-[var(--panel)] p-3">
            <h2 className="mb-2 text-sm font-semibold">Positions</h2>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-zinc-400">
                  <th className="py-1">Ticker</th>
                  <th className="py-1">Qty</th>
                  <th className="py-1">Avg Cost</th>
                  <th className="py-1">Current</th>
                  <th className="py-1">% Change</th>
                  <th className="py-1">P&L</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((position) => (
                  <tr key={position.ticker} className="border-t border-zinc-700">
                    <td className="py-1">{position.ticker}</td>
                    <td className="py-1">{toTwo(position.quantity)}</td>
                    <td className="py-1">{formatCurrency(position.avg_cost)}</td>
                    <td className="py-1">{formatCurrency(position.current_price)}</td>
                    <td className={`py-1 ${position.unrealized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {toTwo(position.unrealized_pnl_pct)}%
                    </td>
                    <td className={`py-1 ${position.unrealized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {formatCurrency(position.unrealized_pnl)}
                    </td>
                  </tr>
                ))}
                {portfolio.positions.length === 0 && (
                  <tr className="border-t border-zinc-700">
                    <td className="py-2 text-zinc-500" colSpan={6}>
                      No positions yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          <section className="rounded-md border border-zinc-700 bg-[var(--panel)] p-3">
            <h2 className="mb-2 text-sm font-semibold">AI Assistant</h2>
            <div className="mb-2 h-56 overflow-y-auto rounded border border-zinc-700 bg-black/20 p-2 text-[11px]">
              {chatMessages.map((message, index) => (
                <div key={`${message.text}-${index}`} className="mb-2">
                  <strong className={message.role === "assistant" ? "text-emerald-300" : "text-blue-300"}>{message.role}</strong>
                  <p>{message.text}</p>
                  {message.details?.map((detail) => (
                    <p className="text-zinc-300" key={detail}>
                      • {detail}
                    </p>
                  ))}
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                className="flex-1 rounded border border-zinc-600 bg-black/25 px-2 py-1 text-xs"
                placeholder="Ask FinAlly..."
                value={chatMessage}
                onChange={(event) => setChatMessage(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void sendChat();
                }}
              />
              <button
                className="rounded bg-purple-700 px-3 py-1 text-xs"
                onClick={() => void sendChat()}
                disabled={chatLoading}
              >
                {chatLoading ? "..." : "Send"}
              </button>
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}
