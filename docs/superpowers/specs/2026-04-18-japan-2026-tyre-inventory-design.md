# Japanese Grand Prix 2026 — Tyre Inventory

## Purpose

Add the Japanese Grand Prix (round 3, Suzuka, 2026-03-27 to 2026-03-29) as the third end-to-end-built race of the 2026 season, completing the opening triple (Australia → China → Japan).

This is data-additive work on top of the multi-featured-race plumbing that was generalised during the China 2026 work. There are no new features, schema changes, or UI changes — only another featured race.

## Out of scope

- Schema or manifest-format changes (none required).
- New chart types, driver views, or analytics tabs.
- Changes to the `seasons/download_f1.py` catalogue (the opportunistic full-season downloader remains unchanged).
- Sprint-weekend logic (Japan 2026 is a regular weekend — FP1/FP2/FP3/Q/R).

## Race facts

| Field          | Value                                     |
|----------------|-------------------------------------------|
| Slug           | `japan-2026`                              |
| Round          | 3                                         |
| Name           | Japanese Grand Prix                       |
| Circuit        | Suzuka                                    |
| Country        | Japan                                     |
| Start date     | 2026-03-27 (Friday)                       |
| End date       | 2026-03-29 (Sunday)                       |
| Weekend format | Regular (no sprint)                       |
| Session keys   | FP1, FP2, FP3, Q, R                       |

Folder and session names follow the existing archive convention:

- `race_dir`: `2026/2026-03-29_Japanese_Grand_Prix`
- Sessions:
  - `2026-03-27_Practice_1`
  - `2026-03-27_Practice_2`
  - `2026-03-28_Practice_3`
  - `2026-03-28_Qualifying`
  - `2026-03-29_Race`

The race took place roughly three weeks before this spec (today is 2026-04-18), so the F1 live-timing archive is expected to have the metadata available.

## Changes

### Sync points (four lists extended)

These four lists must stay in lockstep per `CLAUDE.md`. Each gets one new entry for Japan.

1. **`seasons/fetch_race.py`** — append to `FEATURED_RACES`:
   ```python
   FeaturedRace(
       race_dir="2026/2026-03-29_Japanese_Grand_Prix",
       sessions=(
           "2026-03-27_Practice_1",
           "2026-03-27_Practice_2",
           "2026-03-28_Practice_3",
           "2026-03-28_Qualifying",
           "2026-03-29_Race",
       ),
   ),
   ```

2. **`precompute/src/f1/build.py`** — append to `FEATURED_RACES`:
   ```python
   FeaturedRace(
       slug="japan-2026",
       race_dir="2026/2026-03-29_Japanese_Grand_Prix",
       season=2026,
       round_number=3,
   ),
   ```

3. **`Makefile`** — update `FEATURED_SLUGS`:
   ```make
   FEATURED_SLUGS := australia-2026 china-2026 japan-2026
   ```

4. **`site/src/config.ts`** — extend `FEATURED_RACE_SLUGS`:
   ```ts
   export const FEATURED_RACE_SLUGS: readonly string[] = [
     "australia-2026",
     "china-2026",
     "japan-2026",
   ] as const;
   ```

### Tests: existing "non-featured" fixtures must move off `japan-2026`

Three tests currently use `japan-2026` as a stable example of a **non-featured** race. Once Japan is featured, these assertions and fixtures are wrong. They must be updated — not removed — so the disabled-tile rendering path stays covered.

Non-featured stand-in: **`japan-2025`** (real past race present in `site/src/data/schedule.ts`, reliably absent from the featured list).

- **`site/tests/unit/config.test.ts`**
  - Update `FEATURED_RACE_SLUGS` equality expectation to `["australia-2026", "china-2026", "japan-2026"]`.
  - Add `expect(isFeatured("japan-2026")).toBe(true)` to the true-assertion set.
  - In the false-assertion, replace `"japan-2026"` with `"japan-2025"`.

- **`site/tests/unit/RaceTile.test.tsx`**
  - Change only the `base.slug` from `japan-2026` to `japan-2025`. The other fields are cosmetic for this test (which asserts on "Coming soon" presence and link absence, not on any specific field value), so leave them as-is. The test's behaviour (disabled tile for non-featured, link for featured) is unchanged.

- **`site/tests/e2e/home.spec.ts`** — retarget the non-featured tile E2E:
  - Change `page.goto("/season/2026")` → `page.goto("/season/2025")`.
  - Locator continues to match Japanese Grand Prix (present in 2025 as a non-featured race), so the `hasText: /Japanese Grand Prix/` filter still works. If 2025's tile text differs, adjust the regex.
  - Rationale for retargeting instead of deleting: the E2E test exercises real rendering of a season page's disabled-tile grid; the unit test only renders the tile in isolation. Preserving real-browser coverage is cheap.

### Tests: add Japan drill-in E2E

Append a fourth drill-in test to `site/tests/e2e/home.spec.ts`, mirroring the Australia and China tests exactly:

```ts
test("drill into 2026 → Japanese GP → Tyre Inventory", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /2026/ }).click();
  await expect(page).toHaveURL(/\/season\/2026$/);

  await page.getByRole("link", { name: /Japanese Grand Prix/ }).click();
  await expect(page).toHaveURL(/\/race\/japan-2026$/);
  await expect(page.getByRole("heading", { name: /Japanese Grand Prix/ })).toBeVisible();

  await page.getByRole("link", { name: /Tyre Inventory/ }).click();
  await expect(page).toHaveURL(/\/race\/japan-2026\/tyres$/);
  const cards = page.locator('a[href^="/race/japan-2026/driver/"]');
  await expect(cards).toHaveCount(22);
});
```

## Verification

- `make fetch-race` pulls the four metadata files for all three featured races, including Japan, with no `missing` reports.
- `make precompute` writes `precompute/out/japan-2026.json` alongside the existing two.
- `make test-py` passes (coverage gate ≥ 85% — no code changes in Python, only data, so no regression expected).
- `make test-site` (vitest) passes with the updated non-featured references.
- `make test-e2e` passes all four drill-in flows plus the retargeted non-featured tile test.
- `make build` produces `site/dist/` with `japan-2026.json` copied into `site/public/data/`.

## Risks

- **Archive availability.** If F1's live-timing archive does not expose the Japan metadata at the guessed paths (wrong folder date, different session-name casing), `make fetch-race` reports `missing` files. Mitigation: run `make fetch-race` first and inspect output before the rest of the plan.
- **Weekend-format assumption.** This spec assumes Japan 2026 is a regular weekend (FP1/FP2/FP3/Q/R), matching 2024's format. If the 2026 calendar actually makes Japan a sprint round, the session list in `fetch_race.py` is wrong (Practice_2 and Practice_3 would not exist; Sprint_Qualifying and Sprint would). Detection: `make fetch-race` returns `missing` for Practice_2/Practice_3 and nothing for Sprint_Qualifying/Sprint. Mitigation: switch the session list to the sprint pattern used by China 2026.
- **Driver count drift.** The E2E tests assert exactly 22 driver cards. If Japan's `DriverList` has fewer entries (e.g., a replacement not yet ingested), the assertion fails loudly. Mitigation: verify `japan-2026.json` driver count after `make precompute`, adjust the assertion only if the archive itself has fewer than 22.
- **2025 tile locator.** If the 2025 season page does not actually render "Japanese Grand Prix" as a non-featured tile (e.g., different name formatting), the retargeted E2E fails. Mitigation: quickly inspect `/season/2025` during local `make dev` before committing; adjust the locator if needed.

## Implementation ordering

1. Fetch data first (`make fetch-race`) — catches archive issues before any code change.
2. Extend the four sync-point lists.
3. Run `make precompute` → sanity-check `japan-2026.json`.
4. Update the three existing tests (config, RaceTile, E2E non-featured).
5. Add the Japan drill-in E2E.
6. Run `make build` + `make test` end-to-end.
