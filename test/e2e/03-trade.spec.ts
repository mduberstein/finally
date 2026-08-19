import { expect, test } from "@playwright/test";

// Buy/sell scenario from planning/PLAN.md section 12. NVDA is a seeded
// default ticker, so it always has a live simulator price. Cash assertions
// are directional only — the simulator moves prices roughly twice a
// second, so an exact post-trade balance is not predictable.

const TICKER = "NVDA";
const QUANTITY = "3";

function parseFormattedNumber(text: string): number {
  return Number.parseFloat(text.replace(/,/g, ""));
}

test("trade: buy shares, observe cash/positions/heatmap, then sell them back", async ({ page }) => {
  await page.goto("/");

  const cashLabel = page.getByText("Cash", { exact: true });
  const cashValue = cashLabel.locator("xpath=following-sibling::span[1]");

  // Wait for the header cash figure to render an actual formatted number
  // before reading it.
  await expect(cashValue).toHaveText(/^[\d,]+\.\d{2}$/);
  const preBuyCash = parseFormattedNumber(await cashValue.innerText());

  const positionsSection = page.locator("section", {
    has: page.getByRole("heading", { name: "Positions" }),
  });

  // Buy.
  await page.locator("#trade-ticker").fill(TICKER);
  await page.locator("#trade-quantity").fill(QUANTITY);
  await page.getByRole("button", { name: "Buy", exact: true }).click();

  // Three independent consequences of the buy.
  await expect(positionsSection.getByText("No open positions")).not.toBeVisible();
  await expect(positionsSection.getByText(TICKER, { exact: true })).toBeVisible();
  await expect(page.getByTitle(new RegExp(`^${TICKER} — `))).toBeVisible();

  // The header updates on the portfolio refetch, not synchronously with
  // the click, so this comparison is a polling assertion.
  await expect
    .poll(async () => parseFormattedNumber(await cashValue.innerText()), { timeout: 15_000 })
    .toBeLessThan(preBuyCash);

  const postBuyCash = parseFormattedNumber(await cashValue.innerText());

  // Sell the same shares back. Fields were cleared by the successful buy,
  // so both inputs are refilled.
  await page.locator("#trade-ticker").fill(TICKER);
  await page.locator("#trade-quantity").fill(QUANTITY);
  await page.getByRole("button", { name: "Sell", exact: true }).click();

  // The position row disappears and the empty state returns — this is the
  // regression guard for the epsilon fix in _apply_sell that prevents a
  // near-zero ghost position after selling a whole holding.
  await expect(positionsSection.getByText(TICKER, { exact: true })).not.toBeVisible();
  await expect(positionsSection.getByText("No open positions")).toBeVisible();

  await expect
    .poll(async () => parseFormattedNumber(await cashValue.innerText()), { timeout: 15_000 })
    .toBeGreaterThan(postBuyCash);
});
