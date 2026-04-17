import { test, expect } from "@playwright/test";

test("home renders season tiles including 2026", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Seasons" })).toBeVisible();
  await expect(page.getByRole("link", { name: /2026/ })).toBeVisible();
});

test("drill into 2026 → Australian GP → Tyre Inventory", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /2026/ }).click();
  await expect(page).toHaveURL(/\/season\/2026$/);

  await page.getByRole("link", { name: /Australian Grand Prix/ }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026$/);
  await expect(page.getByRole("heading", { name: /Australian Grand Prix/ })).toBeVisible();

  await page.getByRole("link", { name: /Tyre Inventory/ }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026\/tyres$/);
  const cards = page.locator('a[href^="/race/australia-2026/driver/"]');
  await expect(cards).toHaveCount(22);
});

test("non-featured race tile is disabled and shows Coming soon", async ({ page }) => {
  await page.goto("/season/2026");
  const japaneseTile = page.locator('div[aria-disabled="true"]', { hasText: /Japanese Grand Prix/ });
  await expect(japaneseTile).toBeVisible();
  await expect(japaneseTile).toContainText(/Coming soon/i);
});
