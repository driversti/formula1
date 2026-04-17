import { test, expect } from "@playwright/test";

test("unknown driver TLA renders the NotFound page", async ({ page }) => {
  await page.goto("/race/australia-2026/driver/ZZZ");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});

test("unknown route renders the NotFound page", async ({ page }) => {
  await page.goto("/totally-unknown");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});

test("unknown race slug renders NotFound", async ({ page }) => {
  await page.goto("/race/does-not-exist");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});
