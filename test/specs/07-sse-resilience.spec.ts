import { expect, test } from "@playwright/test";
import { expectPriceToMove, openTerminal } from "../helpers/terminal";

const STREAM = "**/api/stream/prices";
const PRICE_CELL = "watchlist-price-AAPL";

/**
 * The stream is cut by failing the connection itself, so recovery runs through
 * the browser's own `EventSource` retry rather than anything the page does.
 *
 * Not `context.setOffline`: Chromium's offline emulation does not disturb a
 * response that is already streaming. Measured against this container, prices
 * kept arriving for 16 seconds after going offline and the status stayed
 * "connected" - correctly, because nothing had actually dropped.
 */
test("a failing stream shows reconnecting, then recovers without a reload", async ({ page }) => {
  await openTerminal(page);
  await expectPriceToMove(page, PRICE_CELL);

  const status = page.getByTestId("connection-status");
  await expect(status).toHaveAttribute("data-status", "connected");

  let attempts = 0;
  await page.route(STREAM, (route) => {
    attempts += 1;
    return route.abort("connectionfailed");
  });
  await page.reload();

  await expect(status).toHaveAttribute("data-status", "reconnecting");
  // Prices fall back to the values the REST watchlist supplied and stop moving.
  const frozen = await page.getByTestId(PRICE_CELL).textContent();

  // EventSource keeps retrying on its own while the endpoint is unreachable.
  await expect
    .poll(() => attempts, { timeout: 30_000, message: "the client stopped retrying" })
    .toBeGreaterThan(1);

  await page.unroute(STREAM);

  // Recovery is the client's doing: no reload, no user action.
  await expect(status).toHaveAttribute("data-status", "connected", { timeout: 30_000 });
  await expect
    .poll(() => page.getByTestId(PRICE_CELL).textContent(), {
      timeout: 20_000,
      message: "prices did not resume after reconnecting",
    })
    .not.toBe(frozen);
});

/**
 * The third status the contract defines. An unreachable endpoint leaves
 * `EventSource` retrying; a fatal response closes it for good.
 */
test("a stream endpoint returning 500 shows the disconnected state", async ({ page }) => {
  await openTerminal(page);
  const status = page.getByTestId("connection-status");

  await page.route(STREAM, (route) =>
    route.fulfill({ status: 500, contentType: "text/plain", body: "stream down" }),
  );
  await page.reload();

  await expect(status).toHaveAttribute("data-status", "disconnected", { timeout: 30_000 });
  // The REST-backed panels are unaffected by a dead stream.
  await expect(page.getByTestId("header-cash")).not.toHaveText("—");
  await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();

  await page.unroute(STREAM);
  await page.reload();
  await expect(status).toHaveAttribute("data-status", "connected", { timeout: 30_000 });
});
