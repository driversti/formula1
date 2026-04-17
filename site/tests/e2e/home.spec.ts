import { test, expect } from "@playwright/test";

test("home grid shows 22 driver cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Australian Grand Prix/ })).toBeVisible();
  // Each DriverCard is an anchor with an href that starts with /driver/
  const cards = page.locator('a[href^="/driver/"]');
  await expect(cards).toHaveCount(22);
});

test("clicking a card navigates to the driver detail page", async ({ page }) => {
  await page.goto("/");
  const first = page.locator('a[href^="/driver/"]').first();
  const href = await first.getAttribute("href");
  await first.click();
  await expect(page).toHaveURL(new RegExp(href!));
});
