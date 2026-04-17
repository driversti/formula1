import { test, expect } from "@playwright/test";

test("breadcrumbs appear on every route and navigate up the hierarchy", async ({ page }) => {
  await page.goto("/");

  const nav = page.getByRole("navigation", { name: "Breadcrumb" });
  await expect(nav).toBeVisible();

  // On home the only crumb is the current, non-link "Home".
  await expect(nav.getByText("Home")).toHaveAttribute("aria-current", "page");

  // Drill in: season → race → tyres.
  await page.getByRole("link", { name: /^2026$/ }).first().click();
  await expect(page).toHaveURL(/\/season\/2026$/);
  await expect(nav.getByText("2026")).toHaveAttribute("aria-current", "page");

  await page.getByRole("link", { name: /Australian Grand Prix/ }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026$/);
  await expect(nav.getByText("Australian GP")).toHaveAttribute("aria-current", "page");

  await page.getByRole("link", { name: /Tyre Inventory/ }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026\/tyres$/);
  await expect(nav.getByText("Tyres")).toHaveAttribute("aria-current", "page");

  // Hop back up via the header.
  await nav.getByRole("link", { name: "Australian GP" }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026$/);

  await nav.getByRole("link", { name: "2026" }).click();
  await expect(page).toHaveURL(/\/season\/2026$/);

  await nav.getByRole("link", { name: "Home" }).click();
  await expect(page).toHaveURL(/\/$/);
});

test("header bar is sticky on a long page", async ({ page }) => {
  await page.goto("/race/australia-2026/tyres");
  const header = page.locator("header").first();
  await expect(header).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 2000));
  await expect(header).toBeInViewport();
});
