/**
 * Pure chat copy constants, send gating, and transcript-assembly helpers.
 * Every chat sentence the UI shows lives here, never inline in a component,
 * mirroring `lib/trade.ts` and `lib/watchlistForm.ts`. No fetch, no React
 * import, and no clock read — every timestamp arrives as a caller-supplied
 * ISO string, matching `lib/flash.ts`'s `nextFlashState(prev, direction,
 * now)` time-injected convention.
 */

/** A record persisted actions the assistant executed may carry. Kept
 * permissive (all keys optional) so Plan 04 narrows it into a discriminated
 * union once it renders action cards, rather than replacing this shape. */
export interface ChatAction {
  type?: string;
  status?: string;
  ticker?: string;
  [key: string]: unknown;
}

/** One transcript entry, mirroring a `GET /api/chat/history` array element. */
export interface ChatMessageRecord {
  role: "user" | "assistant";
  content: string;
  actions: ChatAction[] | null;
  created_at: string;
}

/** The body of a `POST /api/chat` response. */
export interface ChatReply {
  message: string;
  actions: ChatAction[];
}

/** Mirrors Plan 01's server-side cap so the client never composes a body
 * the server will refuse. */
export const MAX_CHAT_MESSAGE_LENGTH = 4000;

export const CHAT_SEND_FAILED_MESSAGE = "Couldn't reach the assistant — try again.";

export const CHAT_EMPTY_STATE_MESSAGE =
  "Ask about your portfolio, or tell me to buy, sell, or edit your watchlist.";

export const CHAT_INPUT_PLACEHOLDER = "Ask about your portfolio, or tell me to trade...";

/**
 * True only when the trimmed draft is non-empty, at or under the length
 * cap, and no request is currently in flight.
 */
export function canSendChatMessage(draft: string, submitting: boolean): boolean {
  if (submitting) return false;
  const trimmed = draft.trim();
  return trimmed.length > 0 && trimmed.length <= MAX_CHAT_MESSAGE_LENGTH;
}

/**
 * Append an optimistic user bubble. Returns a new array; `messages` is
 * never mutated.
 */
export function appendUserMessage(
  messages: readonly ChatMessageRecord[],
  text: string,
  createdAt: string,
): ChatMessageRecord[] {
  return [
    ...messages,
    { role: "user", content: text.trim(), actions: null, created_at: createdAt },
  ];
}

/**
 * Append the assistant's reply. Returns a new array; `messages` is never
 * mutated.
 */
export function appendAssistantReply(
  messages: readonly ChatMessageRecord[],
  reply: ChatReply,
  createdAt: string,
): ChatMessageRecord[] {
  return [
    ...messages,
    { role: "assistant", content: reply.message, actions: reply.actions, created_at: createdAt },
  ];
}

/**
 * Roll back the most recent message — the panel's response to a send that
 * never reached the server, since nothing was persisted for it. Returns an
 * empty array rather than throwing when given one.
 */
export function dropLastMessage(
  messages: readonly ChatMessageRecord[],
): ChatMessageRecord[] {
  if (messages.length === 0) return [];
  return messages.slice(0, -1);
}
