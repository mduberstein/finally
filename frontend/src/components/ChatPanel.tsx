"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Panel } from "./Panel";
import { clock } from "@/lib/format";
import type { ChatAction, ChatMessage } from "@/lib/types";

const SUGGESTIONS = [
  "How is my portfolio doing?",
  "Buy 10 shares of NVDA",
  "Add PYPL to my watchlist",
];

interface ChatPanelProps {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  onSend: (message: string) => void;
}

/**
 * The assistant column. Prose is set in the humanist face — the one place in
 * the terminal where something other than a machine is speaking.
 */
export function ChatPanel({ messages, loading, error, onSend }: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = scrollRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [messages, loading]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || loading) return;
    onSend(message);
    setDraft("");
  }

  return (
    <Panel title="Assistant" testId="chat-panel" className="bg-chat">
      <div
        ref={scrollRef}
        data-testid="chat-messages"
        className="min-h-0 flex-1 space-y-3 overflow-y-auto p-2"
      >
        {messages.length === 0 && !loading ? (
          <div data-testid="chat-empty" className="space-y-2 pt-2">
            <p className="font-sans text-prose text-ink-dim">
              Ask about your positions, or tell FinAlly what to trade. It can execute orders and
              manage the watchlist for you.
            </p>
            <div className="flex flex-wrap gap-1">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setDraft(suggestion)}
                  className="border border-line px-1.5 py-1 text-left text-ink-dim transition-colors hover:border-blue hover:text-blue"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message, index) => (
          <Message key={`${message.created_at}-${index}`} message={message} />
        ))}

        {loading ? (
          <div data-testid="chat-loading" className="flex items-center gap-2 pl-2">
            <span aria-hidden className="h-1.5 w-1.5 animate-pulse bg-accent" />
            <span className="label">Thinking</span>
          </div>
        ) : null}

        {error ? (
          <p data-testid="chat-error" className="border-l-2 border-down pl-2 text-down">
            {error}
          </p>
        ) : null}
      </div>

      <form onSubmit={submit} className="shrink-0 border-t border-line-soft p-1.5">
        <div className="flex gap-1">
          <input
            data-testid="chat-input"
            aria-label="Message FinAlly"
            value={draft}
            placeholder="Message FinAlly"
            onChange={(event) => setDraft(event.target.value)}
            className="min-w-0 flex-1 bg-raise px-2 py-1.5 font-sans text-prose text-ink placeholder:text-ink-faint focus:outline-none"
          />
          <button
            data-testid="chat-send"
            type="submit"
            disabled={loading || draft.trim().length === 0}
            className="bg-purple px-3 text-ink transition-colors hover:bg-purple/80 disabled:opacity-35"
          >
            Send
          </button>
        </div>
      </form>
    </Panel>
  );
}

function Message({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <article
      data-testid="chat-message"
      data-role={message.role}
      className={`border-l-2 pl-2 ${isUser ? "border-line" : "border-blue"}`}
    >
      <div className="flex items-baseline gap-2">
        <span className={`label ${isUser ? "" : "text-blue"}`}>{isUser ? "You" : "FinAlly"}</span>
        <span className="text-micro text-ink-faint">{clock(message.created_at)}</span>
      </div>
      <p className="whitespace-pre-wrap font-sans text-prose text-ink">{message.content}</p>
      {message.actions.length > 0 ? (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {message.actions.map((action, index) => (
            <ActionChip key={index} action={action} />
          ))}
        </div>
      ) : null}
    </article>
  );
}

function ActionChip({ action }: { action: ChatAction }) {
  const executed = action.status === "executed";
  return (
    <span
      data-testid="chat-action-chip"
      data-status={action.status}
      className={`inline-flex items-center gap-1.5 border px-1.5 py-0.5 ${
        executed ? "border-up/50 text-up" : "border-down/50 text-down"
      }`}
    >
      <span aria-hidden>{executed ? "▸" : "×"}</span>
      {action.detail}
    </span>
  );
}
