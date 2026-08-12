import { expect, type Locator, type Page } from "@playwright/test";

/** The ten tickers seeded into a fresh database, per PLAN.md section 7. */
export const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
];

/**
 * "10,000.00" as rendered by the frontend's money formatter, back to 10000.
 * An em dash means the value has not loaded, which is never a number.
 */
export function parseMoney(text: string | null): number {
  const cleaned = (text ?? "").replace(/[,\s+]/g, "");
  const value = Number(cleaned);
  if (!Number.isFinite(value)) throw new Error(`not a money value: ${JSON.stringify(text)}`);
  return value;
}

export async function readMoney(locator: Locator): Promise<number> {
  return parseMoney(await locator.textContent());
}

/**
 * Loads the terminal and waits until it is live: the API-backed panels have
 * rendered and the SSE stream is connected.
 */
export async function openTerminal(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByTestId("header")).toBeVisible();
  await expect(page.getByTestId("header-cash")).not.toHaveText("—");
  // Only rendered when a load failed, so it is meaningful once cash is in.
  await expect(page.getByTestId("api-notice")).toHaveCount(0);
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
}

/**
 * Resolves once a price cell has shown a second, different value. Proves the
 * tape is running without ever asserting a specific price.
 */
export async function expectPriceToMove(page: Page, testId: string): Promise<void> {
  const cell = page.getByTestId(testId);
  await expect(cell).not.toHaveText("—");
  const first = await cell.textContent();
  await expect
    .poll(() => cell.textContent(), { timeout: 20_000, message: `${testId} never changed` })
    .not.toBe(first);
}

/**
 * Starts recording price-flash classes on a cell.
 *
 * The class is held for only about 60ms before the CSS fade takes over, which
 * is too narrow for a polled assertion to catch reliably. A MutationObserver
 * records every appearance instead, so the assertion is on the class the
 * contract specifies rather than on a mid-transition color.
 */
export async function watchFlash(page: Page, testId: string): Promise<() => Promise<string[]>> {
  await page.evaluate((id) => {
    const node = document.querySelector(`[data-testid="${id}"]`);
    if (!node) throw new Error(`no element with data-testid="${id}"`);
    const seen: string[] = [];
    (window as unknown as Record<string, unknown>).__flashSeen = seen;
    new MutationObserver(() => {
      for (const name of ["flash-up", "flash-down"]) {
        if (node.classList.contains(name) && !seen.includes(name)) seen.push(name);
      }
    }).observe(node, { attributes: true, attributeFilter: ["class"] });
  }, testId);

  return () =>
    page.evaluate(
      () => ((window as unknown as Record<string, unknown>).__flashSeen as string[]) ?? [],
    );
}

/** The portfolio as the API reports it. Used to set up and cross-check state. */
export async function fetchPortfolio(page: Page): Promise<{
  cash_balance: number;
  total_value: number;
  positions: { ticker: string; quantity: number; avg_cost: number }[];
}> {
  const response = await page.request.get("/api/portfolio");
  expect(response.status()).toBe(200);
  return response.json();
}

/** Quantity of a ticker currently held, 0 when there is no position. */
export async function heldQuantity(page: Page, ticker: string): Promise<number> {
  const portfolio = await fetchPortfolio(page);
  return portfolio.positions.find((position) => position.ticker === ticker)?.quantity ?? 0;
}

/**
 * Submits a market order through the trade ticket and returns the fill price
 * the UI reported, parsed out of `trade-status`.
 */
export async function tradeViaTicket(
  page: Page,
  ticker: string,
  shares: number,
  side: "buy" | "sell",
): Promise<number> {
  await page.getByTestId("trade-ticker-input").fill(ticker);
  await page.getByTestId("trade-quantity-input").fill(String(shares));
  await page.getByTestId(side === "buy" ? "trade-buy" : "trade-sell").click();

  const verb = side === "buy" ? "Bought" : "Sold";
  const status = page.getByTestId("trade-status");
  await expect(status).toHaveText(new RegExp(`^${verb} [\\d,.]+ ${ticker} at [\\d,]+\\.\\d{2}$`));

  const text = (await status.textContent()) ?? "";
  const price = text.split(" at ").pop();
  return parseMoney(price ?? null);
}
