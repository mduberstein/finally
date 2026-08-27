import { expect, test } from "@playwright/test";

test("FinAlly shell loads and renders key sections", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });

  await expect(page.getByRole("heading", { level: 1, name: "FinAlly" })).toBeVisible();
  await expect(page.getByText("AI Assistant")).toBeVisible();
  await expect(page.getByText("Positions")).toBeVisible();
  await expect(page.getByText("Watchlist")).toBeVisible();
});
