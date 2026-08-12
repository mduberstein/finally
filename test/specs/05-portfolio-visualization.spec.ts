import { expect, test } from "@playwright/test";
import { heldQuantity, openTerminal, tradeViaTicket } from "../helpers/terminal";

// This spec owns these two symbols so it never depends on earlier specs.
const TICKERS = ["JPM", "V"];

/**
 * The computed background of a tile. Chromium resolves `color-mix()` to either
 * `rgb(r, g, b)` or `color(srgb r g b)`; in both, the first two numbers are the
 * red and green components, which is all this assertion needs.
 */
interface Tile {
  title: string;
  red: number;
  green: number;
  width: number;
  height: number;
}

test("the heatmap colors tiles by P&L and the P&L chart plots snapshots", async ({ page }) => {
  await openTerminal(page);

  for (const ticker of TICKERS) {
    expect(await heldQuantity(page, ticker)).toBe(0);
    await tradeViaTicket(page, ticker, 3, "buy");
  }

  // Heatmap: a sized tile per position, colored to match the P&L it reports.
  await expect(page.getByTestId("heatmap-empty")).toHaveCount(0);
  for (const ticker of TICKERS) {
    const tile = page.getByTestId(`heatmap-tile-${ticker}`);
    await expect(tile).toBeVisible();

    // Title and background are read in one pass so a re-render between two
    // separate reads cannot pair a stale sign with a fresh color.
    const measured: Tile = await tile.evaluate((node) => {
      const style = getComputedStyle(node);
      const numbers = (style.backgroundColor.match(/[\d.]+/g) ?? []).map(Number);
      const box = node.getBoundingClientRect();
      return {
        title: node.getAttribute("title") ?? "",
        red: numbers[0],
        green: numbers[1],
        width: box.width,
        height: box.height,
      };
    });

    expect(measured.width).toBeGreaterThan(0);
    expect(measured.height).toBeGreaterThan(0);
    expect(measured.title).toMatch(new RegExp(`^${ticker} [+-][\\d.]+%$`));

    const profitable = measured.title.includes("+");
    if (profitable) {
      expect(measured.green, `${measured.title} should read green`).toBeGreaterThan(measured.red);
    } else {
      expect(measured.red, `${measured.title} should read red`).toBeGreaterThan(measured.green);
    }
  }

  // P&L chart: every trade writes a snapshot, so the series has points.
  const history = await page.request.get("/api/portfolio/history");
  expect(history.status()).toBe(200);
  const { snapshots } = await history.json();
  expect(snapshots.length).toBeGreaterThanOrEqual(2);

  await expect(page.getByTestId("pnl-chart-empty")).toHaveCount(0);
  // The panel's drift figure only renders once snapshots reached the component.
  await expect(page.getByTestId("pnl-chart")).toContainText(/[+-][\d,]+\.\d{2}/);

  const canvases = page.getByTestId("pnl-chart-canvas").locator("canvas");
  await expect(canvases.first()).toBeVisible();
  const size = await canvases.first().evaluate((node: HTMLCanvasElement) => ({
    width: node.width,
    height: node.height,
  }));
  expect(size.width).toBeGreaterThan(0);
  expect(size.height).toBeGreaterThan(0);
});
