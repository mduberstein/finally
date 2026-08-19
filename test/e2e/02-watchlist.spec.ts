import { expect, test } from "@playwright/test";

// Watchlist add/remove scenario from planning/PLAN.md section 12. PYPL is
// used because it is not one of the ten seeded defaults, so adding and
// removing it nets to zero and leaves the database exactly as this spec
// found it for every later spec.

const KNOWN_DEFAULT_TICKER = "AAPL";
const NEW_TICKER = "PYPL";

// Matches only an actual per-ticker remove button's accessible name, never
// a watchlist row's own role="button" wrapper (whose computed accessible
// name falls back to concatenated descendant content — ticker, price,
// change%, then the remove button's own aria-label text). Anchoring with
// ^ and $ requires a full match, so the wrapper's longer concatenated name
// never matches, and this locator counts exactly one element per row.
const REMOVE_BUTTON_PATTERN = /^Remove [A-Z]+ from watchlist$/;

test("watchlist: add a new ticker, reject a duplicate, then remove it", async ({ page }) => {
  await page.goto("/");

  const watchlistSection = page.locator("section", {
    has: page.getByRole("heading", { name: "Watchlist" }),
  });

  // Wait for the watchlist to be populated (not the loading skeleton)
  // before taking the baseline count.
  await expect(
    watchlistSection.getByRole("button", {
      name: "Remove AAPL from watchlist",
      exact: true,
    }),
  ).toBeVisible();

  const removeButtons = watchlistSection.getByRole("button", { name: REMOVE_BUTTON_PATTERN });
  const baselineCount = await removeButtons.count();

  // Add: fill the input, click Add, and confirm the new ticker's remove
  // button appears and the row count grew by exactly one — a duplicate
  // insert would grow the count by two and fail this assertion.
  await page.locator("#watchlist-add-ticker").fill(NEW_TICKER);
  await page.getByRole("button", { name: "Add", exact: true }).click();

  const pypRemoveButton = watchlistSection.getByRole("button", {
    name: "Remove PYPL from watchlist",
    exact: true,
  });
  await expect(pypRemoveButton).toBeVisible();
  await expect(removeButtons).toHaveCount(baselineCount + 1);

  // Negative case: attempting to add a ticker already on the list must
  // reject inline rather than silently succeed. The Add button disables
  // for an already-present ticker, so this goes through the input's Enter
  // handler, which calls the same validation unconditionally.
  await page.locator("#watchlist-add-ticker").fill(KNOWN_DEFAULT_TICKER);
  await page.locator("#watchlist-add-ticker").press("Enter");

  // Scoped to the watchlist section, not page-wide: Next.js renders its own
  // global route-announcer div with role="alert" outside this section, and
  // an unscoped locator resolves to both (strict-mode violation).
  await expect(watchlistSection.getByRole("alert")).toHaveText("AAPL is already on your watchlist.");
  await expect(removeButtons).toHaveCount(baselineCount + 1);

  // Remove: click the added ticker's remove button and confirm it
  // disappears and the row count returns to its pre-add value, restoring
  // the database for every later spec.
  await pypRemoveButton.click();

  await expect(pypRemoveButton).toHaveCount(0);
  await expect(removeButtons).toHaveCount(baselineCount);
});
