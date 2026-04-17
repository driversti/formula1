import { test, expect } from "@playwright/test";

test("driver page shows inventory groups", async ({ page }) => {
  await page.goto("/race/australia-2026/driver/VER");
  await expect(page.getByRole("heading", { name: /Max Verstappen/ })).toBeVisible();
  // At least one of HARD/MEDIUM/SOFT sections should appear.
  const sections = page.locator("h3");
  await expect(sections.first()).toBeVisible();
  // The set cards render SVG usage bars.
  await expect(page.locator("svg").first()).toBeVisible();
});
