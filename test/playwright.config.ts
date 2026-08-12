import { defineConfig, devices } from "@playwright/test";

/**
 * BASE_URL is http://terminal:8000 inside docker-compose.test.yml. For a
 * host-side run against that stack, use http://localhost:18000 (the compose
 * file publishes E2E_PORT, default 18000, rather than colliding on 8000).
 */
const baseURL = process.env.BASE_URL ?? "http://localhost:18000";

export default defineConfig({
  testDir: "./specs",

  // The app is one process with one SQLite database and one shared price
  // cache. Parallel workers would trade against each other's cash balance.
  fullyParallel: false,
  workers: 1,

  // No retries on purpose: a spec that only passes on the second attempt is a
  // defect owned by this suite, not a result to be papered over.
  retries: 0,

  timeout: 60_000,
  expect: { timeout: 15_000 },
  forbidOnly: !!process.env.CI,

  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],

  use: {
    baseURL,
    trace: "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Wide enough for the lg: three-column terminal layout, so the heatmap
        // and charts get real pixel dimensions to lay out into.
        viewport: { width: 1600, height: 1000 },
      },
    },
  ],
});
