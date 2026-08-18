/**
 * Pure chat copy constants, send gating, and transcript-assembly helpers.
 * Every chat sentence the UI shows lives here, never inline in a component,
 * mirroring `lib/trade.ts` and `lib/watchlistForm.ts`. No fetch, no React
 * import, and no clock read — every timestamp arrives as a caller-supplied
 * ISO string, matching `lib/flash.ts`'s `nextFlashState(prev, direction,
 * now)` time-injected convention.
 */

import { formatPrice } from "./format";

const EXECUTED = "executed";

/** One LLM-proposed trade element of the persisted `actions` payload
 * (`backend/app/chat/models.py`'s contract). `price` is present only when
 * `status` is `"executed"`; `code` only when `"failed"`. */
export interface TradeChatAction {
  type: "trade";
  status: "executed" | "failed";
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price?: number;
  code?: string;
}

/** One LLM-proposed watchlist change element of the persisted `actions`
 * payload. `code` is present only when `status` is `"failed"`. */
export interface WatchlistChatAction {
  type: "watchlist";
  status: "executed" | "failed";
  ticker: string;
  action: "add" | "remove";
  code?: string;
}

/** A record persisted actions the assistant executed may carry — narrowed
 * from Plan 02's permissive placeholder into a discriminated union over
 * `type` now that Plan 04 renders action cards from it. */
export type ChatAction = TradeChatAction | WatchlistChatAction;

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

/**
 * The card sentence for one executed action, or null for anything else —
 * a non-executed status, an unrecognized `type`, or a payload missing a
 * required field. This single function is the entire honesty guarantee
 * behind `ChatActionCard` (D-04, T-04-22): the component has no render
 * path other than this function's non-null return, so a card is never
 * shown for something that did not happen. Every field is guarded with a
 * `typeof` check exactly as `tradeErrorMessage` guards a rejection
 * payload — these payloads ultimately originate from a model rather than
 * from this codebase, so an unrecognized shape must produce no card
 * rather than a card reading undefined.
 */
export function actionCardText(action: unknown): string | null {
  if (action === null || typeof action !== "object") return null;
  const payload = action as Record<string, unknown>;
  if (payload.status !== EXECUTED) return null;

  switch (payload.type) {
    case "trade": {
      const ticker = typeof payload.ticker === "string" ? payload.ticker : null;
      const side = payload.side === "buy" || payload.side === "sell" ? payload.side : null;
      const quantity = typeof payload.quantity === "number" ? payload.quantity : null;
      const price = typeof payload.price === "number" ? payload.price : null;
      if (ticker === null || side === null || quantity === null || price === null) return null;

      const verb = side === "buy" ? "Bought" : "Sold";
      return `✓ ${verb} ${quantity} ${ticker} @ $${formatPrice(price)}`;
    }
    case "watchlist": {
      const ticker = typeof payload.ticker === "string" ? payload.ticker : null;
      const watchlistAction =
        payload.action === "add" || payload.action === "remove" ? payload.action : null;
      if (ticker === null || watchlistAction === null) return null;

      const verb = watchlistAction === "add" ? "Added" : "Removed";
      const tail = watchlistAction === "add" ? "to watchlist" : "from watchlist";
      return `✓ ${verb} ${ticker} ${tail}`;
    }
    default:
      return null;
  }
}
