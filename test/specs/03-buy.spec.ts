import { expect, test } from "@playwright/test";
import { openTerminal, readMoney, tradeViaTicket } from "../helpers/terminal";

const SHARES = 2;

test("buying shares moves cash into a position and updates the portfolio", async ({ page }) => {
  await openTerminal(page);

  const cash = page.getByTestId("header-cash");
  const total = page.getByTestId("header-total-value");
  const cashBefore = await readMoney(cash);
  const totalBefore = await readMoney(total);

  const fill = await tradeViaTicket(page, "AAPL", SHARES, "buy");

  // The position exists, in the table and on the heatmap.
  await expect(page.getByTestId("position-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("heatmap-tile-AAPL")).toBeVisible();
  await expect(page.getByTestId("positions-empty")).toHaveCount(0);

  // Cash fell by roughly the notional. The fill price comes from the ticket's
  // own confirmation, so nothing here predicts a price. Precision 1 absorbs
  // the cent of rounding in the displayed price and the displayed balance.
  await expect
    .poll(async () => cashBefore - (await readMoney(cash)), { message: "cash never decreased" })
    .toBeCloseTo(SHARES * fill, 1);

  // Total value is conserved across a market order, up to the tape moving
  // underneath us between the two reads.
  const totalAfter = await readMoney(total);
  expect(Math.abs(totalAfter - totalBefore) / totalBefore).toBeLessThan(0.01);
  expect(totalAfter).toBeGreaterThan(await readMoney(cash));
});

test("a buy larger than the cash balance is rejected with the server's reason", async ({
  page,
}) => {
  await openTerminal(page);
  const cash = page.getByTestId("header-cash");
  const cashBefore = await readMoney(cash);

  await page.getByTestId("trade-ticker-input").fill("NVDA");
  await page.getByTestId("trade-quantity-input").fill("100000");
  await page.getByTestId("trade-buy").click();

  await expect(page.getByTestId("trade-status")).toHaveText(/^Insufficient cash: need \$/);
  expect(await readMoney(cash)).toBe(cashBefore);
});
