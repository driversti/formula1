import { test, expect } from "@playwright/test";

test("Race Strategy tile is reachable from race page", async ({ page }) => {
  await page.goto("/race/australia-2026");
  await page.getByRole("link", { name: /Race Strategy/i }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026\/strategy$/);
  await expect(page.getByRole("img", { name: /Race strategy chart/i })).toBeVisible();
});

test("sprint weekend shows SPRINT/RACE tabs and switching updates the chart", async ({ page }) => {
  await page.goto("/race/china-2026/strategy");
  const raceTab = page.getByRole("button", { name: /^RACE$/ });
  const sprintTab = page.getByRole("button", { name: /^SPRINT$/ });
  await expect(raceTab).toBeVisible();
  await expect(sprintTab).toBeVisible();
  await expect(raceTab).toHaveAttribute("aria-pressed", "true");

  const chart = page.getByRole("img", { name: /Race strategy chart/i });
  await expect(chart).toBeVisible();
  const svgBefore = await chart.innerHTML();

  await sprintTab.click();
  await expect(sprintTab).toHaveAttribute("aria-pressed", "true");
  const svgAfter = await chart.innerHTML();
  expect(svgAfter).not.toEqual(svgBefore);
});

test("non-featured race redirects away from /strategy", async ({ page }) => {
  // bahrain-2025 exists in SCHEDULE but is NOT in FEATURED_RACE_SLUGS,
  // so the Navigate(replace) redirect fires in Strategy.tsx.
  await page.goto("/race/bahrain-2025/strategy");
  await expect(page).toHaveURL(/\/race\/bahrain-2025$/);
});

test("japan-2026 Strategy page shows status strip segments and a band tooltip", async ({ page }) => {
  await page.goto("/race/japan-2026/strategy");
  const chart = page.getByRole("img", { name: /Race strategy chart/i });
  await expect(chart).toBeVisible();

  const stripSegments = page.locator('[data-testid="status-strip-segment"]');
  await expect(stripSegments.first()).toBeVisible({ timeout: 5_000 });
  expect(await stripSegments.count()).toBeGreaterThanOrEqual(1);

  const first = stripSegments.first();
  await first.hover();
  await expect(
    page.getByText(/^(Yellow|Safety Car|Virtual Safety Car|Red Flag) · lap \d+.\d+ \(\d+ laps\)$/),
  ).toBeVisible();
});
