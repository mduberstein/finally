import { expect, test } from "@playwright/test";
import { heldQuantity, openTerminal, readMoney, tradeViaTicket } from "../helpers/terminal";

const TICKER = "MSFT";

test("selling returns cash, shrinks the position, and closes it when flat", async ({ page }) => {
  await openTerminal(page);

  // Self-contained setup: this spec owns MSFT, so it never depends on what an
  // earlier spec left behind.
  expect(await heldQuantity(page, TICKER)).toBe(0);
  await tradeViaTicket(page, TICKER, 4, "buy");
  await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();

  const cash = page.getByTestId("header-cash");
  const quantityCell = page.getByTestId(`position-row-${TICKER}`).locator("> span").nth(1);
  await expect(quantityCell).toHaveText("4");

  // Partial sell: cash up by the notional, position still there but smaller.
  const cashBefore = await readMoney(cash);
  const fill = await tradeViaTicket(page, TICKER, 1, "sell");

  await expect
    .poll(async () => (await readMoney(cash)) - cashBefore, { message: "cash never increased" })
    .toBeCloseTo(fill, 1);
  await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();
  await expect(quantityCell).toHaveText("3");
  expect(await heldQuantity(page, TICKER)).toBe(3);

  // Closing sell: the row and the heatmap tile go away entirely.
  await tradeViaTicket(page, TICKER, 3, "sell");

  await expect(page.getByTestId(`position-row-${TICKER}`)).toHaveCount(0);
  await expect(page.getByTestId(`heatmap-tile-${TICKER}`)).toHaveCount(0);
  expect(await heldQuantity(page, TICKER)).toBe(0);
});

test("selling more shares than are held is rejected with the server's reason", async ({ page }) => {
  await openTerminal(page);

  await page.getByTestId("trade-ticker-input").fill("NFLX");
  await page.getByTestId("trade-quantity-input").fill("5");
  await page.getByTestId("trade-sell").click();

  await expect(page.getByTestId("trade-status")).toHaveText(
    /^Insufficient shares: tried to sell 5 NFLX, hold 0$/,
  );
  await expect(page.getByTestId("position-row-NFLX")).toHaveCount(0);
});
