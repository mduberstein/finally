/**
 * Fix for WR-03 (`.planning/phases/03-visual-terminal-watchlist-control/03-REVIEW.md`):
 * removing the currently-selected ticker from the watchlist must clear the
 * selection. Without this, `MainChart`'s header keeps rendering the removed
 * ticker's symbol, price, and change percent — frozen at whatever value it
 * held at removal, because `usePriceStream`'s `prices` map is never pruned
 * and the backend `MarketFeed` stops requesting quotes for off-watchlist
 * tickers. A frozen, no-longer-tracked price is actively misleading in a
 * trading UI.
 */

/**
 * Return `null` when the removed ticker is the current selection, otherwise
 * return `current` unchanged (same reference, so React can bail out of a
 * redundant re-render).
 */
export function clearSelectionIfRemoved(current: string | null, removed: string): string | null {
  if (current === removed) return null;
  return current;
}

/**
 * Sibling to `clearSelectionIfRemoved` for the refetch case (Plan 04): a
 * chat-driven watchlist change can drop the currently-charted ticker
 * without the frontend ever learning its identity directly, only that the
 * refreshed ticker list no longer contains it. Return `null` when
 * `current` is non-null and absent from `tickers`, otherwise return
 * `current` unchanged (same reference, so React can bail out of a
 * redundant re-render) — the same reference-stability contract as the
 * existing helper.
 */
export function clearSelectionIfAbsent(
  current: string | null,
  tickers: readonly string[],
): string | null {
  if (current !== null && !tickers.includes(current)) return null;
  return current;
}
