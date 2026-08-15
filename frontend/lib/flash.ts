import type { PriceTick } from "./types";

/** How long a price flash tint takes to fade back to the panel background. */
export const FLASH_DURATION_MS = 500;

export interface FlashState {
  direction: "up" | "down";
  startedAt: number;
}

/**
 * Derive the next flash state from a new tick. Pure and time-injected —
 * `now` is always a parameter, never read inside — so the rapid-restart
 * behavior is testable without timers or fake clocks.
 *
 * A flat tick neither starts a new flash nor cancels a running one; an up
 * or down tick always (re)starts the flash from `now`, even mid-fade.
 */
export function nextFlashState(
  prev: FlashState | null,
  direction: PriceTick["direction"],
  now: number,
): FlashState | null {
  if (direction === "flat") return prev;
  return { direction, startedAt: now };
}

/** True while the flash tint should still be visible. */
export function isFlashActive(state: FlashState | null, now: number): boolean {
  if (state == null) return false;
  return now - state.startedAt < FLASH_DURATION_MS;
}

/**
 * The non-color direction cue: a triangle glyph, matching the arrows used
 * in `backend/market_data_demo.py`. These are geometric shape characters,
 * not emoji.
 */
export function directionGlyph(direction: PriceTick["direction"]): string {
  if (direction === "up") return "▲";
  if (direction === "down") return "▼";
  return "";
}
