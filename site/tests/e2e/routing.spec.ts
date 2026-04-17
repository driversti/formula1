import { test, expect } from "@playwright/test";

test("unknown driver TLA renders the NotFound page", async ({ page }) => {
  await page.goto("/driver/ZZZ");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});

test("unknown route renders the NotFound page", async ({ page }) => {
  await page.goto("/totally-unknown");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});
