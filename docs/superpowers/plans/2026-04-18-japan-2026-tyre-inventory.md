# Japanese Grand Prix 2026 — Tyre Inventory — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `japan-2026` (Round 3, Suzuka, 2026-03-27/28/29) as the third end-to-end-built race of 2026, completing the opening triple alongside `australia-2026` and `china-2026`.

**Architecture:** Data-additive only — no schema, Pydantic, Zod, or UI changes. Extend the four featured-race sync-point lists (`seasons/fetch_race.py`, `precompute/src/f1/build.py`, `Makefile`, `site/src/config.ts`), update the three tests that use `japan-2026` as a stable non-featured example, and add a new Japan drill-in E2E mirroring Australia/China.

**Tech Stack:** Python 3.13 (uv), pytest · TypeScript 5 (Vite, React 19, Tailwind) · Vitest · Playwright · Make.

**User preference:** Always ask the user before creating any commit (see `~/.claude/CLAUDE.md`). Treat every "Commit" step below as "run `git status` / `git diff`, summarise the change, and request approval before running `git commit`."

**Spec:** [docs/superpowers/specs/2026-04-18-japan-2026-tyre-inventory-design.md](../specs/2026-04-18-japan-2026-tyre-inventory-design.md)

---

## Task 1: Probe the F1 archive before writing code

**Why first:** The spec assumes Japan 2026 is a regular weekend (FP1/FP2/FP3/Q/R) under the folder `2026/2026-03-29_Japanese_Grand_Prix`. If either assumption is wrong, the rest of the plan's literal strings are wrong. A one-off fetch via the existing CLI override catches this now, at zero code-change cost.

**Files:** none modified.

- [ ] **Step 1.1: Fetch the Japan metadata using CLI overrides**

Run from the repo root:

```bash
cd seasons && uv run python fetch_race.py \
  --race-dir 2026/2026-03-29_Japanese_Grand_Prix \
  --sessions 2026-03-27_Practice_1 2026-03-27_Practice_2 \
             2026-03-28_Practice_3 2026-03-28_Qualifying \
             2026-03-29_Race
```

Expected: the script prints five session lines, each with `{'ok': 4, 'cached': 0, 'missing': 0, 'skip': 0}` (or `cached` on a rerun). `Totals:` reports `missing: 0`.

- [ ] **Step 1.2: Inspect the fetched metadata**

Verify the four expected files landed per session:

```bash
ls seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/
```

Expected: `DriverList.jsonStream  SessionInfo.json  TimingAppData.jsonStream  TyreStintSeries.jsonStream`.

Also check that `SessionInfo.json` carries the right meeting:

```bash
cat seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/SessionInfo.json | head -c 500
```

Expected: a JSON payload whose `Meeting.Name` is "Japanese Grand Prix" and `Meeting.Location` is "Suzuka".

- [ ] **Step 1.3: Decision gate — regular vs sprint weekend**

If Step 1.1 printed `missing > 0` for `2026-03-27_Practice_2` or `2026-03-28_Practice_3`, Japan 2026 is **not** a regular weekend. Stop and retry Step 1.1 with the sprint pattern:

```bash
cd seasons && uv run python fetch_race.py \
  --race-dir 2026/2026-03-29_Japanese_Grand_Prix \
  --sessions 2026-03-27_Practice_1 2026-03-27_Sprint_Qualifying \
             2026-03-28_Sprint 2026-03-28_Qualifying \
             2026-03-29_Race
```

If that fetch succeeds, every literal session-name string in Tasks 2 and 3 below must be swapped to the sprint pattern before continuing. If neither pattern works, stop and surface the issue to the user — the archive may not have published the meeting yet.

No commit at the end of Task 1 — nothing is in git. The fetched files are gitignored (per `seasons/.gitignore`).

---

## Task 2: Extend `seasons/fetch_race.py` FEATURED_RACES

**Files:**
- Modify: `seasons/fetch_race.py` (append one entry to `FEATURED_RACES`, lines ~36–57)

- [ ] **Step 2.1: Append Japan to FEATURED_RACES**

In `seasons/fetch_race.py`, replace:

```python
FEATURED_RACES: tuple[FeaturedRace, ...] = (
    FeaturedRace(
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        sessions=(
            "2026-03-06_Practice_1",
            "2026-03-06_Practice_2",
            "2026-03-07_Practice_3",
            "2026-03-07_Qualifying",
            "2026-03-08_Race",
        ),
    ),
    FeaturedRace(
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        sessions=(
            "2026-03-13_Practice_1",
            "2026-03-13_Sprint_Qualifying",
            "2026-03-14_Sprint",
            "2026-03-14_Qualifying",
            "2026-03-15_Race",
        ),
    ),
)
```

with:

```python
FEATURED_RACES: tuple[FeaturedRace, ...] = (
    FeaturedRace(
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        sessions=(
            "2026-03-06_Practice_1",
            "2026-03-06_Practice_2",
            "2026-03-07_Practice_3",
            "2026-03-07_Qualifying",
            "2026-03-08_Race",
        ),
    ),
    FeaturedRace(
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        sessions=(
            "2026-03-13_Practice_1",
            "2026-03-13_Sprint_Qualifying",
            "2026-03-14_Sprint",
            "2026-03-14_Qualifying",
            "2026-03-15_Race",
        ),
    ),
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
)
```

(If Task 1 flipped to the sprint pattern, substitute those five session names instead.)

- [ ] **Step 2.2: Verify the default fetch now covers all three races**

Run:

```bash
make fetch-race
```

Expected: three "Fetching …" blocks, one per race. `Totals:` reports `missing: 0`. Japan's three new sessions are all `ok` on first run; Australia and China are all `cached`.

- [ ] **Step 2.3: Commit (ask first per CLAUDE.md)**

```bash
git add seasons/fetch_race.py
git commit -m "feat(seasons): fetch Japanese GP 2026 metadata by default"
```

---

## Task 3: Extend `precompute/src/f1/build.py` FEATURED_RACES and produce `japan-2026.json`

**Files:**
- Modify: `precompute/src/f1/build.py` (append one entry to `FEATURED_RACES`, lines ~214–227)

- [ ] **Step 3.1: Append Japan to FEATURED_RACES**

In `precompute/src/f1/build.py`, replace:

```python
FEATURED_RACES: tuple[FeaturedRace, ...] = (
    FeaturedRace(
        slug="australia-2026",
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
    ),
    FeaturedRace(
        slug="china-2026",
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
    ),
)
```

with:

```python
FEATURED_RACES: tuple[FeaturedRace, ...] = (
    FeaturedRace(
        slug="australia-2026",
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
    ),
    FeaturedRace(
        slug="china-2026",
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
    ),
    FeaturedRace(
        slug="japan-2026",
        race_dir="2026/2026-03-29_Japanese_Grand_Prix",
        season=2026,
        round_number=3,
    ),
)
```

- [ ] **Step 3.2: Build all three manifests**

Run:

```bash
make precompute
```

Expected stdout contains three `wrote …/precompute/out/<slug>.json` lines, including `japan-2026.json`. Exit code 0.

- [ ] **Step 3.3: Sanity-check the Japan manifest**

Run:

```bash
cd precompute && uv run python -c "
import json, pathlib
m = json.loads(pathlib.Path('out/japan-2026.json').read_text())
r = m['race']
print('slug=', r['slug'])
print('name=', r['name'])
print('location=', r['location'])
print('round=', r['round'])
print('date=', r['date'])
print('session keys=', [s['key'] for s in r['sessions']])
print('drivers=', len(r['drivers']))
"
```

Expected output:

```
slug= japan-2026
name= Japanese Grand Prix
location= Suzuka
round= 3
date= 2026-03-29
session keys= ['FP1', 'FP2', 'FP3', 'Q', 'R']
drivers= 22
```

(If the printed `drivers` count is not 22, note the actual number — the E2E in Task 6 will use it.)

- [ ] **Step 3.4: Run the Python test suite**

Run:

```bash
make test-py
```

Expected: all tests green, coverage ≥ 85%. No new tests are needed here because we only appended data; `build.py`'s logic is unchanged and already covered by the China fixture.

- [ ] **Step 3.5: Commit (ask first per CLAUDE.md)**

```bash
git add precompute/src/f1/build.py
git commit -m "feat(precompute): build Japanese GP 2026 manifest"
```

---

## Task 4: Extend `Makefile` FEATURED_SLUGS

**Files:**
- Modify: `Makefile` line 7.

- [ ] **Step 4.1: Add `japan-2026` to FEATURED_SLUGS**

Replace line 7 of `Makefile`:

```make
FEATURED_SLUGS := australia-2026 china-2026
```

with:

```make
FEATURED_SLUGS := australia-2026 china-2026 japan-2026
```

- [ ] **Step 4.2: Verify the site pulls in all three manifests**

Run:

```bash
make clean && make build
```

Expected: `site/dist/` is produced without error. Check the copied manifests:

```bash
ls site/public/data/
```

Expected output: `australia-2026.json  china-2026.json  japan-2026.json` (order irrelevant).

- [ ] **Step 4.3: Commit (ask first per CLAUDE.md)**

```bash
git add Makefile
git commit -m "feat(make): copy Japanese GP 2026 manifest into site data"
```

---

## Task 5: Extend `site/src/config.ts` and update `config.test.ts`

**Files:**
- Modify: `site/src/config.ts` (lines 11–14).
- Modify: `site/tests/unit/config.test.ts` (lines 5, 11, 15).

- [ ] **Step 5.1: Update the unit test first (TDD)**

Replace the contents of `site/tests/unit/config.test.ts` with:

```ts
import { describe, it, expect } from "vitest";
import { FEATURED_RACE_SLUGS, isFeatured } from "../../src/config";

describe("featured-race config", () => {
  it("lists australia-2026, china-2026, and japan-2026 as the featured slugs", () => {
    expect(FEATURED_RACE_SLUGS).toEqual([
      "australia-2026",
      "china-2026",
      "japan-2026",
    ]);
  });

  it("isFeatured returns true for each featured slug", () => {
    expect(isFeatured("australia-2026")).toBe(true);
    expect(isFeatured("china-2026")).toBe(true);
    expect(isFeatured("japan-2026")).toBe(true);
  });

  it("isFeatured returns false for slugs not in the list", () => {
    expect(isFeatured("japan-2025")).toBe(false);
    expect(isFeatured("")).toBe(false);
  });
});
```

- [ ] **Step 5.2: Run the test and confirm it fails**

Run:

```bash
cd site && npx vitest run tests/unit/config.test.ts
```

Expected: two failing assertions — `FEATURED_RACE_SLUGS` still equals the two-item array, and `isFeatured("japan-2026")` still returns `false`.

- [ ] **Step 5.3: Update the source**

Replace lines 11–14 of `site/src/config.ts`:

```ts
export const FEATURED_RACE_SLUGS: readonly string[] = [
  "australia-2026",
  "china-2026",
] as const;
```

with:

```ts
export const FEATURED_RACE_SLUGS: readonly string[] = [
  "australia-2026",
  "china-2026",
  "japan-2026",
] as const;
```

- [ ] **Step 5.4: Run the test and confirm it passes**

Run:

```bash
cd site && npx vitest run tests/unit/config.test.ts
```

Expected: 3 passing assertions, 0 failing.

- [ ] **Step 5.5: Commit (ask first per CLAUDE.md)**

```bash
git add site/src/config.ts site/tests/unit/config.test.ts
git commit -m "feat(site): feature Japanese GP 2026 in FEATURED_RACE_SLUGS"
```

---

## Task 6: Swap the `RaceTile` unit-test fixture off `japan-2026`

**Why:** After Task 5, `japan-2026` is featured. The `RaceTile` unit test uses it as a stable **non-featured** example to verify the "Coming soon" disabled-tile path. Switch to `japan-2025`, a real past race that is not (and will not be) in `FEATURED_RACE_SLUGS`.

**Files:**
- Modify: `site/tests/unit/RaceTile.test.tsx` (line 7 only).

- [ ] **Step 6.1: Update the fixture slug**

In `site/tests/unit/RaceTile.test.tsx`, change line 7 from:

```tsx
  slug: "japan-2026",
```

to:

```tsx
  slug: "japan-2025",
```

Leave every other field untouched — the test does not assert on them.

- [ ] **Step 6.2: Run the test and confirm it passes**

Run:

```bash
cd site && npx vitest run tests/unit/RaceTile.test.tsx
```

Expected: both cases pass (disabled tile for `japan-2025`, link for the overridden `australia-2026`).

- [ ] **Step 6.3: Commit (ask first per CLAUDE.md)**

```bash
git add site/tests/unit/RaceTile.test.tsx
git commit -m "test(site): move RaceTile non-featured fixture to japan-2025"
```

---

## Task 7: Retarget the non-featured E2E and add the Japan drill-in E2E

**Why:**
- The existing non-featured E2E targets `/season/2026` and expects a disabled Japanese tile. With Japan featured, 2026 no longer has any disabled tiles (the 2026 catalogue has exactly three races, all featured). Retarget the test to `/season/2025`, which still has Japanese GP as a non-featured entry.
- The positive drill-in path for Japan needs coverage equivalent to the Australia and China E2Es.

**Files:**
- Modify: `site/tests/e2e/home.spec.ts` (retarget non-featured test + append Japan drill-in).

- [ ] **Step 7.1: Retarget the non-featured tile E2E**

In `site/tests/e2e/home.spec.ts`, replace this block (lines 39–44):

```ts
test("non-featured race tile is disabled and shows Coming soon", async ({ page }) => {
  await page.goto("/season/2026");
  const japaneseTile = page.locator('div[aria-disabled="true"]', { hasText: /Japanese Grand Prix/ });
  await expect(japaneseTile).toBeVisible();
  await expect(japaneseTile).toContainText(/Coming soon/i);
});
```

with:

```ts
test("non-featured race tile is disabled and shows Coming soon", async ({ page }) => {
  await page.goto("/season/2025");
  const japaneseTile = page.locator('div[aria-disabled="true"]', { hasText: /Japanese Grand Prix/ });
  await expect(japaneseTile).toBeVisible();
  await expect(japaneseTile).toContainText(/Coming soon/i);
});
```

- [ ] **Step 7.2: Add the Japan drill-in E2E**

Append the following test at the end of `site/tests/e2e/home.spec.ts`:

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

**If Task 3 Step 3.3 reported a driver count other than 22**, change the final expectation to that number (e.g., `toHaveCount(20)`).

- [ ] **Step 7.3: Run the full Playwright suite**

Run:

```bash
make test-e2e
```

Expected: all five tests pass — home-renders-seasons, Australia drill-in, China drill-in, Japan drill-in, non-featured tile on 2025.

If the non-featured test fails because `/season/2025` renders Japanese GP with different copy than the regex expects, narrow the regex (e.g., `{ hasText: /Japanese/ }`) until it matches — do NOT widen it to a non-specific string like `/Grand Prix/` because that matches other races too.

- [ ] **Step 7.4: Commit (ask first per CLAUDE.md)**

```bash
git add site/tests/e2e/home.spec.ts
git commit -m "test(site): add Japanese GP drill-in E2E and retarget non-featured test"
```

---

## Task 8: Full pipeline verification and final commit

**Files:** none modified (verification only).

- [ ] **Step 8.1: Run the complete test matrix from a clean state**

Run:

```bash
make clean && make test
```

Expected: Python tests green (≥ 85% coverage), vitest green, Playwright green.

- [ ] **Step 8.2: Verify the manifest copy is complete**

Run:

```bash
ls site/public/data/
```

Expected: `australia-2026.json`, `china-2026.json`, `japan-2026.json` (all three present, none missing).

- [ ] **Step 8.3: Eyeball the dev server once (optional but recommended)**

Run:

```bash
make dev
```

Visit `http://localhost:5173/`, click 2026 → Japanese Grand Prix → Tyre Inventory, and confirm the grid renders 22 driver cards with team colours. Stop the server (Ctrl-C).

- [ ] **Step 8.4: Nothing more to commit**

Confirm a clean tree with `git status`. Everything else has been committed in Tasks 2–7.

---

## Self-review notes

- Spec coverage: every bullet under "Changes" in the spec has a task (fetch_race.py → T2, build.py → T3, Makefile → T4, config.ts → T5, config.test.ts → T5, RaceTile.test.tsx → T6, home.spec.ts retarget → T7, home.spec.ts new drill-in → T7). Probe and verification are T1 and T8.
- Placeholder scan: every code block is concrete; every command has exact expected output; no "TBD" or "similar to above".
- Type consistency: every literal (slug `japan-2026`, race_dir `2026/2026-03-29_Japanese_Grand_Prix`, round `3`, date `2026-03-29`) appears identically in every task that references it.
- Sprint-weekend escape hatch is documented in T1 Step 1.3 and referenced from T2 Step 2.1.
