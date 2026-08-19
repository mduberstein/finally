import { expect, test } from "@playwright/test";

// AI-executed trade scenario from planning/PLAN.md section 12. The harness
// runs the app container with LLM_MOCK=true, so backend/app/chat/llm.py's
// mock_response short-circuits before any network call — this scenario is
// fully offline and deterministic (T-05-18).

test("ai chat: a natural-language buy is executed and confirmed", async ({ page }) => {
  await page.goto("/");

  const chatSection = page.locator("section", {
    has: page.getByRole("heading", { name: "AI Copilot" }),
  });
  const messageInput = page.locator("#chat-message-input");

  // The panel fetches history on mount and does not render its input row
  // until that resolves.
  await expect(messageInput).toBeVisible();

  // This shape matches the mock's trade regex exactly (a side word,
  // whitespace, a whole-number digit run, then a ticker) and produces a
  // byte-identical response every time.
  await messageInput.fill("buy 2 AAPL");
  await chatSection.getByRole("button", { name: "Send", exact: true }).click();

  // 1. The user's own message appears in the transcript.
  await expect(chatSection.getByText("buy 2 AAPL", { exact: true })).toBeVisible();

  // 2. An assistant bubble appears containing the mock's exact reply text.
  await expect(chatSection.getByText("Mock: buy 2 AAPL.")).toBeVisible();

  // 3. An executed-trade confirmation card appears — its presence is the
  // proof the trade actually went through, since the card only renders
  // when the action's status is executed.
  await expect(chatSection.getByText(/Bought 2 AAPL/)).toBeVisible();

  // 4. The trade actually reached the portfolio.
  const positionsSection = page.locator("section", {
    has: page.getByRole("heading", { name: "Positions" }),
  });
  await expect(positionsSection.getByText("AAPL", { exact: true })).toBeVisible();

  // Negative half: a message matching none of the mock's shapes produces
  // the fixed fallback reply and no confirmation card, pinning the mock's
  // no-action behavior.
  const actionCards = chatSection.getByText(/^✓ /);
  await expect(actionCards).toHaveCount(1);

  await messageInput.fill("What's my portfolio worth?");
  await chatSection.getByRole("button", { name: "Send", exact: true }).click();

  await expect(
    chatSection.getByText("Mock response: portfolio and watchlist unchanged."),
  ).toBeVisible();
  await expect(actionCards).toHaveCount(1);
});
