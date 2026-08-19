import { expect, test } from "@playwright/test";

// Fresh-start scenario from planning/PLAN.md section 12: default watchlist
// appears, starting cash is shown, the connection indicator reads
// Connected, and prices are actually streaming (not merely fetched once).
// This file must run first under playwright.config.ts's single worker, so
// it asserts against the pristine seeded database before any later spec
// mutates cash or positions.

const DEFAULT_TICKERS = [
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

test("fresh start: default watchlist, starting cash, live connection, streaming prices", async ({
  page,
}) => {
  await page.goto("/");

  // Ten default tickers, located by their exact remove-button accessible
  // name — the aria-label form, not text matching, because the ticker "V"
  // would match as a substring almost everywhere else on the page.
  // exact: true is required: the row's own role="button" wrapper has no
  // aria-label, so its computed accessible name falls back to concatenated
  // descendant content, which includes the nested remove button's
  // aria-label text — a substring match against that name would resolve
  // to both the row and the button (strict-mode violation).
  for (const ticker of DEFAULT_TICKERS) {
    await expect(
      page.getByRole("button", { name: `Remove ${ticker} from watchlist`, exact: true }),
    ).toBeVisible();
  }

  // Header's Cash label is followed by the formatted starting balance. No
  // dollar sign — frontend/lib/format.ts formatPrice returns a grouped
  // two-decimal string with no currency symbol. Scoped to the sibling span
  // that immediately follows the Cash label: on a fresh portfolio, cash
  // and total value are both 10,000.00, so an unscoped text match resolves
  // to both figures.
  const cashLabel = page.getByText("Cash", { exact: true });
  const cashValue = cashLabel.locator("xpath=following-sibling::span[1]");
  await expect(cashValue).toHaveText("10,000.00");

  // Connection indicator's status region reads Connected.
  const connectionStatus = page.getByRole("status");
  await expect(connectionStatus).toHaveText("Connected");

  // Prices are actually streaming, not merely fetched once: capture the
  // watchlist section's rendered text, then poll until it differs from the
  // captured value.
  const watchlistSection = page.locator("section", { has: page.getByRole("heading", { name: "Watchlist" }) });
  const initialText = await watchlistSection.innerText();
  await expect
    .poll(async () => watchlistSection.innerText(), { timeout: 15_000 })
    .not.toBe(initialText);

  // A price cell acquires one of the two flash animation classes within
  // the expect timeout — together with the text-change poll above, this
  // proves both that new values arrive and that the UI reacts to them.
  await expect(watchlistSection.locator(".animate-flash-up, .animate-flash-down").first()).toBeVisible({
    timeout: 15_000,
  });

  // Positions panel shows its empty state, confirming the database really
  // is fresh.
  const positionsSection = page.locator("section", { has: page.getByRole("heading", { name: "Positions" }) });
  await expect(positionsSection.getByText("No open positions")).toBeVisible();
});
