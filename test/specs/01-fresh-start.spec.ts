import { expect, test } from "@playwright/test";
import { DEFAULT_TICKERS, expectPriceToMove, openTerminal, watchFlash } from "../helpers/terminal";

/**
 * The only spec that requires a virgin database. `run.sh` recreates the app
 * container with a tmpfs database on every run, and the numeric filename
 * prefix keeps this first under `workers: 1`. If it fails on the seeded values
 * while later specs pass, the database was reused rather than reseeded.
 */
test("fresh start shows the seeded watchlist, $10,000 cash, and a running tape", async ({
  page,
}) => {
  await openTerminal(page);

  const rows = page.getByTestId("watchlist").locator('[data-testid^="watchlist-row-"]');
  await expect(rows).toHaveCount(DEFAULT_TICKERS.length);
  for (const ticker of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
  }

  await expect(page.getByTestId("header-cash")).toHaveText("10,000.00");
  await expect(page.getByTestId("header-total-value")).toHaveText("10,000.00");
  await expect(page.getByTestId("positions-empty")).toBeVisible();
  await expect(page.getByTestId("heatmap-empty")).toBeVisible();

  // Prices are visibly streaming: the number changes, and the cell flashes.
  const readFlashes = await watchFlash(page, "watchlist-price-AAPL");
  await expectPriceToMove(page, "watchlist-price-AAPL");
  await expect
    .poll(readFlashes, { timeout: 20_000, message: "price cell never gained a flash class" })
    .not.toHaveLength(0);

  const flashes = await readFlashes();
  expect(flashes.every((name) => name === "flash-up" || name === "flash-down")).toBe(true);
});

test("clicking a watchlist row selects it for the main chart", async ({ page }) => {
  await openTerminal(page);

  await page.getByTestId("watchlist-row-NVDA").click();

  await expect(page.getByTestId("watchlist-row-NVDA")).toHaveAttribute("data-selected", "true");
  await expect(page.getByTestId("main-chart")).toContainText("NVDA");
  await expect(page.getByTestId("main-chart-price")).not.toHaveText("—");
});
