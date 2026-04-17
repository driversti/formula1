# Breadcrumb Header Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent, sticky site header with a plain-link breadcrumb trail on every route of the Formula 1 Dashboard site, giving users a one-click path back up the season → race → analytics hierarchy.

**Architecture:** A new `AppShell` layout route wraps all existing routes via a React Router `<Outlet />`. `SiteHeader` renders a brand (linking to `/`) on the left and `Breadcrumbs` on the right. Breadcrumbs derive their trail from `useLocation().pathname` + the existing `SCHEDULE` lookup via a pure `buildTrail()` helper; current item is non-link text with `aria-current="page"`. Narrow viewports use horizontal scroll rather than label shortening.

**Tech Stack:** React 19, React Router 7 (`createBrowserRouter`, nested `<Outlet />`), TypeScript (strict), Tailwind CSS 4, vitest + @testing-library/react, Playwright.

**Spec:** `docs/superpowers/specs/2026-04-17-breadcrumb-header-design.md`

---

## File Structure

| File | Responsibility |
|---|---|
| `site/src/lib/breadcrumbs.ts` | Pure `buildTrail(pathname, schedule)` returning `Crumb[]`, plus `useBreadcrumbs()` hook wiring it to `useLocation()`. |
| `site/src/components/Breadcrumbs.tsx` | `<nav aria-label="Breadcrumb">` + ordered list. Links for non-current; text with `aria-current="page"` for current. Horizontal scroll on overflow. |
| `site/src/components/SiteHeader.tsx` | Sticky `<header>` bar — brand (red square + wordmark, links to `/`) on the left, `<Breadcrumbs />` on the right. |
| `site/src/components/AppShell.tsx` | Layout component: `<SiteHeader />` above `<Outlet />`. |
| `site/src/App.tsx` (modified) | Restructure router so every existing route is a child of a layout route that renders `<AppShell />`. |
| `site/tests/unit/breadcrumbs.test.ts` | Pathname → trail unit tests for `buildTrail`. |
| `site/tests/unit/Breadcrumbs.test.tsx` | Component tests (MemoryRouter) — `aria-current`, link hrefs, `aria-label`. |
| `site/tests/e2e/breadcrumbs.spec.ts` | Playwright: drill in, then use header crumbs to hop back up. |

All other files (routes, data, schemas) are untouched.

---

## Task 1: `buildTrail` pure function + unit tests

**Files:**
- Create: `site/src/lib/breadcrumbs.ts`
- Create: `site/tests/unit/breadcrumbs.test.ts`

- [ ] **Step 1.1: Write the failing tests**

Create `site/tests/unit/breadcrumbs.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { buildTrail } from "../../src/lib/breadcrumbs";
import { SCHEDULE } from "../../src/data/schedule";

describe("buildTrail", () => {
  it("returns just Home for /", () => {
    expect(buildTrail("/", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: true },
    ]);
  });

  it("returns Home + year (current) for /season/:year", () => {
    expect(buildTrail("/season/2026", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2026", href: "/season/2026", current: true },
    ]);
  });

  it("returns Home > year > race (current) for /race/:slug", () => {
    expect(buildTrail("/race/australia-2026", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2026", href: "/season/2026", current: false },
      { label: "Australian GP", href: "/race/australia-2026", current: true },
    ]);
  });

  it("returns full trail with Tyres leaf for /race/:slug/tyres", () => {
    expect(buildTrail("/race/australia-2026/tyres", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2026", href: "/season/2026", current: false },
      { label: "Australian GP", href: "/race/australia-2026", current: false },
      { label: "Tyres", href: "/race/australia-2026/tyres", current: true },
    ]);
  });

  it("returns full trail with Driver · TLA leaf for /race/:slug/driver/:tla", () => {
    expect(buildTrail("/race/australia-2026/driver/VER", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2026", href: "/season/2026", current: false },
      { label: "Australian GP", href: "/race/australia-2026", current: false },
      { label: "Driver · VER", href: "/race/australia-2026/driver/VER", current: true },
    ]);
  });

  it("uses race.name verbatim when it does not end in 'Grand Prix'", () => {
    // 2020 had a "70th Anniversary Grand Prix" — still ends in Grand Prix.
    // Construct a path with a race that exists in SCHEDULE and verify fallback logic
    // by mocking an ad-hoc schedule.
    const fakeSchedule = [
      {
        year: 2099,
        races: [
          {
            slug: "special-2099",
            round: 1,
            name: "Special Event",
            countryCode: "XXX",
            countryName: "Xland",
            circuitShortName: "Xtrack",
            startDate: "2099-01-01",
            endDate: "2099-01-02",
          },
        ],
        driversChampion: null,
        constructorsChampion: null,
        raceCount: 1,
      },
    ];
    expect(buildTrail("/race/special-2099", fakeSchedule)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "2099", href: "/season/2099", current: false },
      { label: "Special Event", href: "/race/special-2099", current: true },
    ]);
  });

  it("falls back to Home-only for an unknown slug", () => {
    expect(buildTrail("/race/does-not-exist", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: true },
    ]);
  });

  it("falls back to Home-only for an unknown year", () => {
    expect(buildTrail("/season/1999", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: true },
    ]);
  });

  it("falls back to Home-only for a completely unknown path", () => {
    expect(buildTrail("/totally-unknown", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: true },
    ]);
  });
});
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `cd site && npx vitest run tests/unit/breadcrumbs.test.ts`
Expected: FAIL with "Cannot find module '../../src/lib/breadcrumbs'".

- [ ] **Step 1.3: Implement `buildTrail`**

Create `site/src/lib/breadcrumbs.ts`:

```ts
import { useLocation } from "react-router-dom";
import { SCHEDULE, type Season } from "../data/schedule";

export type Crumb = {
  label: string;
  href: string;
  current: boolean;
};

function raceLabel(name: string, countryName: string): string {
  return name.endsWith("Grand Prix") ? `${countryName} GP` : name;
}

function homeOnly(): Crumb[] {
  return [{ label: "Home", href: "/", current: true }];
}

export function buildTrail(pathname: string, schedule: Season[]): Crumb[] {
  if (pathname === "/" || pathname === "") return homeOnly();

  const seasonMatch = pathname.match(/^\/season\/(\d+)\/?$/);
  if (seasonMatch) {
    const year = Number(seasonMatch[1]);
    const season = schedule.find((s) => s.year === year);
    if (!season) return homeOnly();
    return [
      { label: "Home", href: "/", current: false },
      { label: String(year), href: `/season/${year}`, current: true },
    ];
  }

  const raceMatch = pathname.match(/^\/race\/([^/]+)(?:\/(tyres|driver\/([A-Za-z0-9]+)))?\/?$/);
  if (raceMatch) {
    const slug = raceMatch[1];
    const leaf = raceMatch[2]; // "tyres" | "driver/XXX" | undefined
    const season = schedule.find((s) => s.races.some((r) => r.slug === slug));
    const race = season?.races.find((r) => r.slug === slug);
    if (!season || !race) return homeOnly();

    const year = season.year;
    const trail: Crumb[] = [
      { label: "Home", href: "/", current: false },
      { label: String(year), href: `/season/${year}`, current: false },
      {
        label: raceLabel(race.name, race.countryName),
        href: `/race/${slug}`,
        current: !leaf,
      },
    ];

    if (leaf === "tyres") {
      trail.push({ label: "Tyres", href: `/race/${slug}/tyres`, current: true });
    } else if (leaf?.startsWith("driver/")) {
      const tla = leaf.slice("driver/".length).toUpperCase();
      trail.push({
        label: `Driver · ${tla}`,
        href: `/race/${slug}/driver/${tla}`,
        current: true,
      });
    }
    return trail;
  }

  return homeOnly();
}

export function useBreadcrumbs(): Crumb[] {
  const { pathname } = useLocation();
  return buildTrail(pathname, SCHEDULE);
}
```

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `cd site && npx vitest run tests/unit/breadcrumbs.test.ts`
Expected: PASS (9 tests).

- [ ] **Step 1.5: Typecheck**

Run: `cd site && npx tsc -b`
Expected: no errors.

- [ ] **Step 1.6: Commit**

```bash
git add site/src/lib/breadcrumbs.ts site/tests/unit/breadcrumbs.test.ts
git commit -m "feat(site): add buildTrail breadcrumb helper"
```

---

## Task 2: `Breadcrumbs` component + tests

**Files:**
- Create: `site/src/components/Breadcrumbs.tsx`
- Create: `site/tests/unit/Breadcrumbs.test.tsx`

- [ ] **Step 2.1: Write the failing component tests**

Create `site/tests/unit/Breadcrumbs.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Breadcrumbs } from "../../src/components/Breadcrumbs";

function renderAt(pathname: string) {
  return render(
    <MemoryRouter initialEntries={[pathname]}>
      <Breadcrumbs />
    </MemoryRouter>,
  );
}

describe("<Breadcrumbs />", () => {
  it("wraps the trail in a <nav> with aria-label='Breadcrumb'", () => {
    renderAt("/");
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
  });

  it("marks the current item with aria-current='page' and renders it as text, not a link", () => {
    renderAt("/race/australia-2026/tyres");
    const current = screen.getByText("Tyres");
    expect(current).toHaveAttribute("aria-current", "page");
    expect(current.tagName).not.toBe("A");
  });

  it("renders non-current items as links with expected hrefs", () => {
    renderAt("/race/australia-2026/tyres");
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(nav).getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
    expect(within(nav).getByRole("link", { name: "2026" })).toHaveAttribute(
      "href",
      "/season/2026",
    );
    expect(within(nav).getByRole("link", { name: "Australian GP" })).toHaveAttribute(
      "href",
      "/race/australia-2026",
    );
  });

  it("renders a single non-linked 'Home' on the home route", () => {
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(nav).queryByRole("link")).toBeNull();
    expect(within(nav).getByText("Home")).toHaveAttribute("aria-current", "page");
  });

  it("includes separators marked aria-hidden between items", () => {
    renderAt("/season/2026");
    const separators = document.querySelectorAll('[aria-hidden="true"]');
    // At least one separator between Home and 2026.
    expect(separators.length).toBeGreaterThanOrEqual(1);
  });
});
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `cd site && npx vitest run tests/unit/Breadcrumbs.test.tsx`
Expected: FAIL with "Cannot find module '../../src/components/Breadcrumbs'".

- [ ] **Step 2.3: Implement `Breadcrumbs`**

Create `site/src/components/Breadcrumbs.tsx`:

```tsx
import { Link } from "react-router-dom";
import { useBreadcrumbs } from "../lib/breadcrumbs";

export function Breadcrumbs() {
  const trail = useBreadcrumbs();

  return (
    <nav
      aria-label="Breadcrumb"
      className="min-w-0 overflow-x-auto whitespace-nowrap text-sm text-f1-muted [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      <ol className="flex items-center gap-1">
        {trail.map((crumb, i) => (
          <li key={crumb.href} className="flex items-center gap-1">
            {i > 0 && (
              <span aria-hidden="true" className="text-f1-border">
                ›
              </span>
            )}
            {crumb.current ? (
              <span
                aria-current="page"
                className="rounded px-1.5 py-0.5 text-compound-medium"
              >
                {crumb.label}
              </span>
            ) : (
              <Link
                to={crumb.href}
                className="rounded px-1.5 py-0.5 text-f1-text hover:bg-white/5"
              >
                {crumb.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
```

Note: `text-compound-medium` is the yellow accent (`#ffdd00`) already defined in `site/src/styles/index.css`.

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `cd site && npx vitest run tests/unit/Breadcrumbs.test.tsx`
Expected: PASS (5 tests).

- [ ] **Step 2.5: Commit**

```bash
git add site/src/components/Breadcrumbs.tsx site/tests/unit/Breadcrumbs.test.tsx
git commit -m "feat(site): add Breadcrumbs component"
```

---

## Task 3: `SiteHeader` component

**Files:**
- Create: `site/src/components/SiteHeader.tsx`

No dedicated unit tests — `SiteHeader` is a thin layout wrapper exercised end-to-end in Task 5. (Creating a test that re-asserts "brand link goes to /" would duplicate what the E2E already covers.)

- [ ] **Step 3.1: Implement `SiteHeader`**

Create `site/src/components/SiteHeader.tsx`:

```tsx
import { Link } from "react-router-dom";
import { Breadcrumbs } from "./Breadcrumbs";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-f1-border bg-f1-panel px-5 py-3">
      <Link to="/" className="flex shrink-0 items-center gap-2 text-sm font-bold tracking-wide">
        <span
          aria-hidden="true"
          className="inline-block h-2.5 w-2.5 rounded-sm bg-compound-soft"
        />
        F1 DASHBOARD
      </Link>
      <Breadcrumbs />
    </header>
  );
}
```

- [ ] **Step 3.2: Typecheck**

Run: `cd site && npx tsc -b`
Expected: no errors.

- [ ] **Step 3.3: Commit**

```bash
git add site/src/components/SiteHeader.tsx
git commit -m "feat(site): add SiteHeader bar"
```

---

## Task 4: `AppShell` layout + wire into router

**Files:**
- Create: `site/src/components/AppShell.tsx`
- Modify: `site/src/App.tsx`

- [ ] **Step 4.1: Create `AppShell`**

Create `site/src/components/AppShell.tsx`:

```tsx
import { Outlet } from "react-router-dom";
import { SiteHeader } from "./SiteHeader";

export function AppShell() {
  return (
    <>
      <SiteHeader />
      <Outlet />
    </>
  );
}
```

- [ ] **Step 4.2: Rewrite `App.tsx` so every existing route is nested under `AppShell`**

Replace the contents of `site/src/App.tsx` with:

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import Seasons from "./routes/Seasons";
import Season from "./routes/Season";
import Race from "./routes/Race";
import Tyres from "./routes/Tyres";
import Driver from "./routes/Driver";
import NotFound from "./routes/NotFound";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

const router = createBrowserRouter(
  [
    {
      element: <AppShell />,
      children: [
        { path: "/", element: <Seasons /> },
        { path: "/season/:year", element: <Season />, errorElement: <NotFound /> },
        { path: "/race/:slug", element: <Race />, errorElement: <NotFound /> },
        { path: "/race/:slug/tyres", element: <Tyres />, errorElement: <NotFound /> },
        { path: "/race/:slug/driver/:tla", element: <Driver />, errorElement: <NotFound /> },
        { path: "*", element: <NotFound /> },
      ],
    },
  ],
  { basename: basename || "/" },
);

export default function App() {
  return <RouterProvider router={router} />;
}
```

- [ ] **Step 4.3: Typecheck**

Run: `cd site && npx tsc -b`
Expected: no errors.

- [ ] **Step 4.4: Run all vitest unit tests**

Run: `cd site && npm run test`
Expected: PASS (previous tests + new breadcrumbs + Breadcrumbs).

- [ ] **Step 4.5: Dev-server smoke-check**

Run in background: `cd site && npm run dev`
Open `http://localhost:5173/`, verify:
1. A header bar appears at the top with "F1 DASHBOARD" on the left and just "Home" (yellow, not a link) on the right.
2. Click a season tile → header now shows `Home › 2026` with 2026 highlighted.
3. Click a race → header shows `Home › 2026 › Australian GP`.
4. Click Tyre Inventory → header shows `Home › 2026 › Australian GP › Tyres`.
5. Click `2026` in the header → returns to the season page.
6. Click `F1 DASHBOARD` → returns to `/`.
7. Scroll a long page (Tyres, 22 drivers) → header stays pinned at the top.
8. Resize browser to ~360px wide → breadcrumb row scrolls horizontally; bar itself does not wrap.

If any of 1–8 fails, stop and fix before committing.

- [ ] **Step 4.6: Commit**

```bash
git add site/src/components/AppShell.tsx site/src/App.tsx
git commit -m "feat(site): wrap routes in AppShell with site header"
```

---

## Task 5: Playwright E2E — breadcrumb navigation

**Files:**
- Create: `site/tests/e2e/breadcrumbs.spec.ts`

- [ ] **Step 5.1: Write the E2E test**

Create `site/tests/e2e/breadcrumbs.spec.ts`:

```ts
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
  // Still visible after scrolling.
  await expect(header).toBeInViewport();
});
```

Note: the existing `home.spec.ts` drill-down test uses `getByRole("link", { name: /2026/ })` from `/` — on Home our breadcrumbs render "Home" (current, not a link) only, so the season tile remains the sole 2026 link on that page and that test is unaffected. From `/season/2026` onward the header does add a "2026" link, but `home.spec.ts` does not re-query "2026" after navigating away from `/`, so there is no collision. No changes needed to existing E2E specs.

- [ ] **Step 5.2: Run the new E2E spec**

Run: `cd site && npx playwright test tests/e2e/breadcrumbs.spec.ts`
Expected: PASS (2 tests).

If Playwright browsers aren't installed, run `npx playwright install --with-deps chromium` first (one-time).

- [ ] **Step 5.3: Run the full E2E suite to confirm no regressions**

Run: `cd site && npm run test:e2e`
Expected: PASS for all specs (home, routing, driver, breadcrumbs).

- [ ] **Step 5.4: Commit**

```bash
git add site/tests/e2e/breadcrumbs.spec.ts
git commit -m "test(site): add e2e coverage for breadcrumb navigation"
```

---

## Task 6: Final verification

**Files:** none modified.

- [ ] **Step 6.1: Run the full test suite from the repo root**

Run: `make test`
Expected: PASS for Python + site unit + Playwright E2E.

- [ ] **Step 6.2: Production build**

Run: `make build`
Expected: success; `site/dist/` produced.

- [ ] **Step 6.3: Verify branch state**

Run: `git log --oneline main..HEAD`
Expected: 5 feat/test commits on top of the spec commit — `feat(site): add buildTrail…`, `feat(site): add Breadcrumbs…`, `feat(site): add SiteHeader…`, `feat(site): wrap routes…`, `test(site): add e2e…`.

- [ ] **Step 6.4: Hand off**

At this point the feature is complete on `feature/breadcrumb-header`. Use `superpowers:finishing-a-development-branch` to decide between direct merge, PR, etc.
