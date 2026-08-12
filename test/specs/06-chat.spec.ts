import { expect, test, type Page } from "@playwright/test";
import { openTerminal } from "../helpers/terminal";

/**
 * Runs against LLM_MOCK=true. Every reply below is quoted from
 * LLM_MOCK_CONTRACT.md. The mock's parser is literal, so these use the symbol
 * and never the company name.
 */

async function send(page: Page, message: string) {
  const before = await page.getByTestId("chat-message").count();
  await page.getByTestId("chat-input").fill(message);
  await page.getByTestId("chat-send").click();
  // One user message and one assistant reply.
  await expect(page.getByTestId("chat-message")).toHaveCount(before + 2);
  await expect(page.getByTestId("chat-loading")).toHaveCount(0);
  await expect(page.getByTestId("chat-error")).toHaveCount(0);
}

test("the assistant answers, and its trade executes and renders inline", async ({ page }) => {
  await openTerminal(page);
  await expect(page.getByTestId("chat-empty")).toBeVisible();

  await send(page, "how is my portfolio doing?");
  const conversational = page.getByTestId("chat-message").last();
  await expect(conversational).toHaveAttribute("data-role", "assistant");
  await expect(conversational).toContainText("Mock mode: no trade or watchlist change requested.");
  await expect(conversational.getByTestId("chat-action-chip")).toHaveCount(0);
  await expect(page.getByTestId("chat-message").first()).toHaveAttribute("data-role", "user");

  // A buy the fresh $10,000 balance can always cover.
  await send(page, "buy 2 shares of AAPL");
  const bought = page.getByTestId("chat-message").last();
  await expect(bought).toHaveAttribute("data-role", "assistant");
  await expect(bought).toContainText("Mock mode: buying 2 AAPL at the market price.");

  const tradeChip = bought.getByTestId("chat-action-chip");
  await expect(tradeChip).toHaveCount(1);
  await expect(tradeChip).toHaveAttribute("data-status", "executed");
  // Never the exact price: the simulator moves it every 500ms.
  await expect(tradeChip).toContainText(/Bought 2 AAPL @ \$[\d,]+\.\d{2}/);

  // The trade is real: the terminal's own panels moved with it.
  await expect(page.getByTestId("position-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("heatmap-tile-AAPL")).toBeVisible();
});

test("the assistant adds a watchlist symbol, and it survives a reload", async ({ page }) => {
  await openTerminal(page);
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);

  await send(page, "add PYPL to the watchlist");
  const added = page.getByTestId("chat-message").last();
  await expect(added).toContainText("Mock mode: adding PYPL to the watchlist.");

  const chip = added.getByTestId("chat-action-chip");
  await expect(chip).toHaveAttribute("data-status", "executed");
  await expect(chip).toContainText("Added PYPL to the watchlist");
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();

  // Asking again fails, and the failure is reported as a chip, not an error.
  await send(page, "add PYPL to the watchlist");
  const repeat = page.getByTestId("chat-message").last().getByTestId("chat-action-chip");
  await expect(repeat).toHaveAttribute("data-status", "failed");
  await expect(repeat).toContainText("PYPL is already on the watchlist");

  // Conversation history is persisted and repopulates the panel.
  const before = await page.getByTestId("chat-message").count();
  await page.reload();
  await openTerminal(page);
  await expect(page.getByTestId("chat-message")).toHaveCount(before);
  await expect(page.getByTestId("chat-empty")).toHaveCount(0);
});
