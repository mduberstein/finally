import { describe, expect, it } from "vitest";

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
} from "./chat";

const NOW = "2026-08-17T12:00:00.000Z";

describe("canSendChatMessage", () => {
  it("is false for an empty draft", () => {
    expect(canSendChatMessage("", false)).toBe(false);
  });

  it("is false for a whitespace-only draft", () => {
    expect(canSendChatMessage("   ", false)).toBe(false);
  });

  it("is true for a non-empty draft when not submitting", () => {
    expect(canSendChatMessage("hi", false)).toBe(true);
  });

  it("is false while submitting, even with a valid draft", () => {
    expect(canSendChatMessage("hi", true)).toBe(false);
  });

  it("is false for a draft one character over the cap", () => {
    const overLong = "a".repeat(MAX_CHAT_MESSAGE_LENGTH + 1);
    expect(canSendChatMessage(overLong, false)).toBe(false);
  });

  it("is true for a draft exactly at the cap", () => {
    const atCap = "a".repeat(MAX_CHAT_MESSAGE_LENGTH);
    expect(canSendChatMessage(atCap, false)).toBe(true);
  });
});

describe("appendUserMessage", () => {
  it("appends a trimmed user message without mutating the input array", () => {
    const messages: ChatMessageRecord[] = [];
    const next = appendUserMessage(messages, "  hi  ", NOW);
    expect(next).toHaveLength(1);
    expect(next[0]).toEqual({ role: "user", content: "hi", actions: null, created_at: NOW });
    expect(messages).toHaveLength(0);
  });
});

describe("appendAssistantReply", () => {
  it("appends the assistant reply with its actions array", () => {
    const messages: ChatMessageRecord[] = [];
    const next = appendAssistantReply(messages, { message: "ok", actions: [] }, NOW);
    expect(next).toHaveLength(1);
    expect(next[0]).toEqual({ role: "assistant", content: "ok", actions: [], created_at: NOW });
  });
});

describe("dropLastMessage", () => {
  it("drops the final message from a non-empty array", () => {
    const messages: ChatMessageRecord[] = [
      { role: "user", content: "hi", actions: null, created_at: NOW },
      { role: "assistant", content: "hello", actions: [], created_at: NOW },
    ];
    expect(dropLastMessage(messages)).toEqual([messages[0]]);
  });

  it("returns an empty array rather than throwing on an empty array", () => {
    expect(dropLastMessage([])).toEqual([]);
  });
});

describe("copy constants", () => {
  it("matches the UI-SPEC send-failure sentence", () => {
    expect(CHAT_SEND_FAILED_MESSAGE).toBe("Couldn't reach the assistant — try again.");
  });

  it("matches the UI-SPEC empty-state sentence", () => {
    expect(CHAT_EMPTY_STATE_MESSAGE).toBe(
      "Ask about your portfolio, or tell me to buy, sell, or edit your watchlist.",
    );
  });

  it("matches the UI-SPEC input placeholder", () => {
    expect(CHAT_INPUT_PLACEHOLDER).toBe("Ask about your portfolio, or tell me to trade...");
  });
});
