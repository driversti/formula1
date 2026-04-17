import { test, expect } from "@playwright/test";

test("footer 'Read more' navigates to /legal", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/unofficial fan site/i)).toBeVisible();
  await page.getByRole("link", { name: /read more/i }).click();
  await expect(page).toHaveURL(/\/legal$/);
  await expect(page.getByRole("heading", { level: 1, name: /legal/i })).toBeVisible();
});

test("legal page shows all six sections, attribution links, and breadcrumb", async ({ page }) => {
  await page.goto("/legal");

  for (const name of [
    /trademark/i,
    /no affiliation/i,
    /purpose/i,
    /data source/i,
    /code/i,
    /contact/i,
  ]) {
    await expect(page.getByRole("heading", { level: 2, name })).toBeVisible();
  }

  const mailto = page.getByRole("link", { name: /copyright@seniorjava\.dev/i });
  await expect(mailto).toHaveAttribute("href", "mailto:copyright@seniorjava.dev");

  await expect(
    page.getByRole("link", { name: /github\.com\/driversti\/formula1/i }),
  ).toHaveAttribute("href", "https://github.com/driversti/formula1");

  const nav = page.getByRole("navigation", { name: "Breadcrumb" });
  await expect(nav).toContainText("Home");
  await expect(nav).toContainText("Legal");
});
