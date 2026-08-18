"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatTypingIndicator } from "@/components/ChatTypingIndicator";
import {
  appendAssistantReply,
  appendUserMessage,
  canSendChatMessage,
  CHAT_EMPTY_STATE_MESSAGE,
  CHAT_INPUT_PLACEHOLDER,
  CHAT_SEND_FAILED_MESSAGE,
  dropLastMessage,
  MAX_CHAT_MESSAGE_LENGTH,
  type ChatMessageRecord,
  type ChatReply,
} from "@/lib/chat";

/**
 * The AI Copilot panel: fetches persisted history on mount, renders a
 * scrolling bubble transcript with a pinned input row, shows typing dots
 * while a `POST /api/chat` request is in flight, and rolls an optimistic
 * user bubble back off on a failed send (T-04-14). Outer chrome — section,
 * heading, `h-64 min-h-64` box — matches every sibling panel exactly, per
 * Phase 3 D-03 and this plan's assumption 1.
 */
export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessageRecord[] | null>(null);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/chat/history")
      .then((response) => {
        if (!response.ok) throw new Error(`chat history fetch failed: ${response.status}`);
        return response.json();
      })
      .then((history: ChatMessageRecord[]) => setMessages(history))
      .catch((fetchError: unknown) => {
        // Same resilience choice as page.tsx's watchlist fetch: fall back to
        // an empty transcript (the empty-state prompt) rather than a hard
        // error screen.
        console.error(fetchError);
        setMessages([]);
      });
  }, []);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ block: "end" });
  }, [messages, submitting]);

  function handleDraftChange(value: string) {
    setDraft(value);
    setError(null);
  }

  async function submitMessage() {
    if (!canSendChatMessage(draft, submitting)) return;

    const text = draft.trim();
    const sentAt = new Date().toISOString();
    setDraft("");
    setMessages((current) => appendUserMessage(current ?? [], text, sentAt));
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
        setMessages((current) => dropLastMessage(current ?? []));
        setDraft(text);
        setError(CHAT_SEND_FAILED_MESSAGE);
        return;
      }

      const reply = (await response.json()) as ChatReply;
      const repliedAt = new Date().toISOString();
      setMessages((current) => appendAssistantReply(current ?? [], reply, repliedAt));
    } catch {
      setMessages((current) => dropLastMessage(current ?? []));
      setDraft(text);
      setError(CHAT_SEND_FAILED_MESSAGE);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h2 className="text-heading mb-4 text-foreground">AI Copilot</h2>

      {messages === null ? (
        <Skeleton className="h-64 min-h-64 w-full" />
      ) : (
        <div className="flex h-64 min-h-64 flex-col">
          {messages.length === 0 && !submitting ? (
            <div className="flex flex-1 items-center justify-center text-center">
              <p className="text-body text-muted-foreground">{CHAT_EMPTY_STATE_MESSAGE}</p>
            </div>
          ) : (
            <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
              {messages.map((message, index) => (
                <ChatMessage key={index} role={message.role} content={message.content} />
              ))}
              {submitting && <ChatTypingIndicator />}
              <div ref={scrollAnchorRef} />
            </div>
          )}

          <div className="shrink-0 flex items-center gap-2 pt-2">
            <label htmlFor="chat-message-input" className="sr-only">
              Message
            </label>
            <Input
              id="chat-message-input"
              value={draft}
              onChange={(event) => handleDraftChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void submitMessage();
                }
              }}
              placeholder={CHAT_INPUT_PLACEHOLDER}
              maxLength={MAX_CHAT_MESSAGE_LENGTH}
              disabled={submitting}
              className="flex-1"
            />
            <Button
              onClick={() => void submitMessage()}
              disabled={!canSendChatMessage(draft, submitting)}
              className="bg-submit text-submit-foreground hover:bg-submit/80"
            >
              Send
            </Button>
          </div>
          {error && (
            <p className="text-body text-down" role="alert">
              {error}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
