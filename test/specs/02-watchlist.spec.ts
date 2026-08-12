import { expect, test } from "@playwright/test";
import { openTerminal } from "../helpers/terminal";

// Not a seeded ticker, and not the symbol the chat spec adds, so the two
// specs cannot collide on a 409.
const SYMBOL = "SHOP";

test("a ticker can be added to the watchlist and removed again", async ({ page }) => {
  await openTerminal(page);
  await expect(page.getByTestId(`watchlist-row-${SYMBOL}`)).toHaveCount(0);

  await page.getByTestId("watchlist-add-input").fill(SYMBOL);
  await page.getByTestId("watchlist-add-submit").click();

  const row = page.getByTestId(`watchlist-row-${SYMBOL}`);
  await expect(row).toBeVisible();
  await expect(page.getByTestId("watchlist-add-error")).toHaveCount(0);
  await expect(page.getByTestId("watchlist-add-input")).toHaveValue("");

  // The feed re-reads the watchlist on every poll, so a just-added symbol
  // starts streaming shortly after. Until then the contract allows a null
  // price, rendered as an em dash.
  await expect(page.getByTestId(`watchlist-price-${SYMBOL}`)).not.toHaveText("—", {
    timeout: 20_000,
  });

  await page.getByTestId(`watchlist-remove-${SYMBOL}`).click();
  await expect(row).toHaveCount(0);

  // The removal reached the server, not just React state.
  await page.reload();
  await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();
  await expect(page.getByTestId(`watchlist-row-${SYMBOL}`)).toHaveCount(0);
});

test("adding a ticker that is already watched shows the server's reason", async ({ page }) => {
  await openTerminal(page);

  await page.getByTestId("watchlist-add-input").fill("AAPL");
  await page.getByTestId("watchlist-add-submit").click();

  await expect(page.getByTestId("watchlist-add-error")).toHaveText(
    "AAPL is already on the watchlist",
  );
  await expect(page.getByTestId("watchlist").locator('[data-testid="watchlist-row-AAPL"]')).toHaveCount(
    1,
  );
});
