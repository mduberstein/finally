"use client";

import "@/lib/fixtures/install";

import { useCallback, useEffect, useState } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";
import { Heatmap } from "@/components/Heatmap";
import { MainChart } from "@/components/MainChart";
import { PnlChart } from "@/components/PnlChart";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar, type TradeResult } from "@/components/TradeBar";
import { Watchlist } from "@/components/Watchlist";
import { ApiError, api } from "@/lib/api";
import { money, quantity } from "@/lib/format";
import { usePriceStream } from "@/lib/priceStore";
import type { ChatMessage, Portfolio, Snapshot, TradeSide, WatchlistEntry } from "@/lib/types";

export default function Terminal() {
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loadingWatchlist, setLoadingWatchlist] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  usePriceStream();

  const loadWatchlist = useCallback(async () => {
    const { tickers } = await api.watchlist();
    setWatchlist(tickers);
    setSelected((current) => current ?? tickers[0]?.ticker ?? null);
  }, []);

  const loadPortfolio = useCallback(async () => {
    const [next, history] = await Promise.all([api.portfolio(), api.history()]);
    setPortfolio(next);
    setSnapshots(history.snapshots);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        await Promise.all([
          loadWatchlist(),
          loadPortfolio(),
          api.chatHistory().then(({ messages: history }) => setMessages(history)),
        ]);
        setNotice(null);
      } catch {
        setNotice("Cannot reach the API. Panels will fill in once it responds.");
      } finally {
        setLoadingWatchlist(false);
      }
    })();
  }, [loadWatchlist, loadPortfolio]);

  const addTicker = useCallback(
    async (ticker: string): Promise<string | null> => {
      try {
        const entry = await api.addTicker(ticker);
        setWatchlist((current) => [...current, entry]);
        return null;
      } catch (error) {
        return error instanceof ApiError ? error.message : "Could not add that symbol.";
      }
    },
    [],
  );

  const removeTicker = useCallback(
    async (ticker: string) => {
      await api.removeTicker(ticker).catch(() => undefined);
      setWatchlist((current) => current.filter((entry) => entry.ticker !== ticker));
      setSelected((current) => (current === ticker ? null : current));
    },
    [],
  );

  const trade = useCallback(
    async (ticker: string, shares: number, side: TradeSide): Promise<TradeResult> => {
      try {
        const { trade: filled } = await api.trade({ ticker, quantity: shares, side });
        await loadPortfolio();
        const verb = side === "buy" ? "Bought" : "Sold";
        return {
          ok: true,
          message: `${verb} ${quantity(filled.quantity)} ${filled.ticker} at ${money(filled.price)}`,
        };
      } catch (error) {
        return {
          ok: false,
          message: error instanceof ApiError ? error.message : "Trade failed.",
        };
      }
    },
    [loadPortfolio],
  );

  const sendChat = useCallback(
    async (message: string) => {
      const sentAt = new Date().toISOString();
      setMessages((current) => [
        ...current,
        { role: "user", content: message, actions: [], created_at: sentAt },
      ]);
      setChatLoading(true);
      setChatError(null);

      try {
        const reply = await api.chat(message);
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: reply.message,
            actions: reply.actions,
            created_at: reply.created_at,
          },
        ]);
        if (reply.actions.length > 0) {
          await Promise.all([loadPortfolio(), loadWatchlist()]);
        }
      } catch (error) {
        setChatError(error instanceof ApiError ? error.message : "The assistant is unavailable.");
      } finally {
        setChatLoading(false);
      }
    },
    [loadPortfolio, loadWatchlist],
  );

  return (
    <div className="flex min-h-dvh flex-col gap-px bg-void lg:h-dvh lg:overflow-hidden">
      <Header portfolio={portfolio} />

      {notice ? (
        <p data-testid="api-notice" className="bg-panel px-3 py-1 text-accent">
          {notice}
        </p>
      ) : null}

      <main className="grid min-h-0 flex-1 gap-px lg:grid-cols-[15rem_minmax(0,1fr)_21rem] lg:grid-rows-[minmax(0,1fr)]">
        <Watchlist
          entries={watchlist}
          loading={loadingWatchlist}
          selected={selected}
          onSelect={setSelected}
          onAdd={addTicker}
          onRemove={removeTicker}
        />

        <div className="grid min-h-0 min-w-0 gap-px lg:grid-rows-[minmax(0,1.25fr)_minmax(0,1fr)_minmax(0,0.9fr)]">
          <div className="min-h-72 lg:min-h-0">
            <MainChart ticker={selected} />
          </div>
          <div className="grid min-h-0 gap-px sm:grid-cols-2 lg:grid-rows-[minmax(0,1fr)]">
            <div className="min-h-56 lg:min-h-0">
              <Heatmap
                positions={portfolio?.positions ?? []}
                selected={selected}
                onSelect={setSelected}
              />
            </div>
            <div className="min-h-56 lg:min-h-0">
              <PnlChart snapshots={snapshots} />
            </div>
          </div>
          <div className="min-h-56 lg:min-h-0">
            <PositionsTable
              positions={portfolio?.positions ?? []}
              selected={selected}
              onSelect={setSelected}
            />
          </div>
        </div>

        <div className="min-h-96 lg:min-h-0">
          <ChatPanel
            messages={messages}
            loading={chatLoading}
            error={chatError}
            onSend={sendChat}
          />
        </div>
      </main>

      <TradeBar selected={selected} onTrade={trade} />
    </div>
  );
}
