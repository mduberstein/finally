import { expect, test } from "@playwright/test";
import { openTerminal } from "../helpers/terminal";

/**
 * The static mount only exists when a real frontend build is present, so these
 * two only mean anything at the container level. Requested by
 * backend-api-engineer: both are the classic ways this breaks.
 */

test("a deep path reloads into the app rather than a 404", async ({ page }) => {
  await openTerminal(page);

  const shell = await (await page.request.get("/")).text();
  const deep = await page.request.get("/positions/AAPL");
  expect(deep.status()).toBe(200);
  expect(await deep.text()).toBe(shell);

  // Byte-identical HTML is not the same as a working page: hydrate it too.
  await page.goto("/positions/AAPL");
  await expect(page.getByTestId("header")).toBeVisible();
  await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("header-cash")).not.toHaveText("—");
});

test("an unknown /api path returns a JSON 404, never the HTML shell", async ({ page }) => {
  // If a catch-all ever shadows the API, every failed fetch starts returning
  // HTML and the frontend fails in a way that looks like a frontend bug.
  //
  // The status and the content type are what this spec is really about, and
  // both are the backend's. The body is Starlette's stock 404 rather than
  // anything app/ emits: if only that line fails, look for a custom 404
  // handler added to create_app(), not for a broken static mount.
  for (const path of ["/api/nonsense", "/api/stream/nonsense"]) {
    const response = await page.request.get(path);
    expect(response.status(), `${path} status`).toBe(404);
    expect(response.headers()["content-type"], `${path} content-type`).toContain(
      "application/json",
    );
    expect(await response.json(), `${path} body`).toEqual({ detail: "Not Found" });
  }
});
