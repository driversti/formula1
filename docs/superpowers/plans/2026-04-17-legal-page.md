# Legal Page & Site Footer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a site-wide footer disclaimer and a `/legal` route covering trademark disclaimer, no-affiliation statement, purpose, data source attribution, open-source pointer, and takedown contact.

**Architecture:** Static React components rendered via the existing `AppShell` + `react-router-dom` router. Footer mounted once in `AppShell`; legal page is a new route. No data fetching, no Zod. Breadcrumbs updated to recognise `/legal`.

**Tech Stack:** React 19, TypeScript (strict), Vite, Tailwind v4, `react-router-dom` v7, Vitest + Testing Library (unit), Playwright (E2E).

**Spec:** `docs/superpowers/specs/2026-04-17-legal-page-design.md`

---

## File Structure

**New:**
- `site/src/components/SiteFooter.tsx` — muted footer with disclaimer text + link to `/legal`.
- `site/src/routes/Legal.tsx` — static legal page with six sections.
- `site/tests/unit/SiteFooter.test.tsx` — renders disclaimer + `/legal` link.
- `site/tests/unit/Legal.test.tsx` — renders section headings, contact mailto, GitHub link, livetiming attribution.
- `site/tests/e2e/legal.spec.ts` — footer link navigation, section visibility, breadcrumb trail.

**Modified:**
- `site/src/components/AppShell.tsx` — mount `<SiteFooter />` below `<Outlet />`.
- `site/src/App.tsx` — register `/legal` route inside the `AppShell` children.
- `site/src/lib/breadcrumbs.ts` — add `/legal` → `Home / Legal` trail.
- `site/tests/unit/breadcrumbs.test.ts` — cover the new `/legal` trail case.

---

## Task 1: Breadcrumbs support for `/legal`

**Files:**
- Modify: `site/src/lib/breadcrumbs.ts`
- Test: `site/tests/unit/breadcrumbs.test.ts`

- [ ] **Step 1: Write the failing test**

Append to `site/tests/unit/breadcrumbs.test.ts` inside the existing `describe("buildTrail", ...)`:

```ts
  it("returns Home > Legal (current) for /legal", () => {
    expect(buildTrail("/legal", SCHEDULE)).toEqual([
      { label: "Home", href: "/", current: false },
      { label: "Legal", href: "/legal", current: true },
    ]);
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run from `site/`: `npm run test -- breadcrumbs`
Expected: new test FAILS (trail falls back to `homeOnly`).

- [ ] **Step 3: Add the `/legal` branch to `buildTrail`**

Edit `site/src/lib/breadcrumbs.ts`. Add this branch immediately before the final `return homeOnly();` at the end of `buildTrail`:

```ts
  if (pathname === "/legal" || pathname === "/legal/") {
    return [
      { label: "Home", href: "/", current: false },
      { label: "Legal", href: "/legal", current: true },
    ];
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run from `site/`: `npm run test -- breadcrumbs`
Expected: all `breadcrumbs` tests PASS.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/breadcrumbs.ts site/tests/unit/breadcrumbs.test.ts
git commit -m "feat(site): recognise /legal in breadcrumb trail"
```

---

## Task 2: `SiteFooter` component

**Files:**
- Create: `site/src/components/SiteFooter.tsx`
- Test: `site/tests/unit/SiteFooter.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `site/tests/unit/SiteFooter.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SiteFooter } from "../../src/components/SiteFooter";

function renderFooter() {
  return render(
    <MemoryRouter>
      <SiteFooter />
    </MemoryRouter>,
  );
}

describe("<SiteFooter />", () => {
  it("renders inside a <footer> landmark", () => {
    renderFooter();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("contains the unofficial-fan-site disclaimer", () => {
    renderFooter();
    expect(
      screen.getByText(/unofficial fan site/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/trademarks belong to their respective owners/i),
    ).toBeInTheDocument();
  });

  it("links 'Read more' to /legal", () => {
    renderFooter();
    const link = screen.getByRole("link", { name: /read more/i });
    expect(link).toHaveAttribute("href", "/legal");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from `site/`: `npm run test -- SiteFooter`
Expected: FAIL (`SiteFooter` module does not exist).

- [ ] **Step 3: Implement `SiteFooter`**

Create `site/src/components/SiteFooter.tsx`:

```tsx
import { Link } from "react-router-dom";

export function SiteFooter() {
  return (
    <footer className="mt-8 border-t border-f1-border bg-f1-panel px-5 py-3 text-xs text-f1-muted">
      <p>
        Unofficial fan site. All trademarks belong to their respective owners.{" "}
        <Link to="/legal" className="text-f1-text underline hover:text-compound-soft">
          Read more
        </Link>
      </p>
    </footer>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run from `site/`: `npm run test -- SiteFooter`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add site/src/components/SiteFooter.tsx site/tests/unit/SiteFooter.test.tsx
git commit -m "feat(site): add SiteFooter with trademark disclaimer"
```

---

## Task 3: `Legal` route

**Files:**
- Create: `site/src/routes/Legal.tsx`
- Test: `site/tests/unit/Legal.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `site/tests/unit/Legal.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Legal from "../../src/routes/Legal";

function renderLegal() {
  return render(
    <MemoryRouter>
      <Legal />
    </MemoryRouter>,
  );
}

describe("<Legal />", () => {
  it("renders the page heading", () => {
    renderLegal();
    expect(screen.getByRole("heading", { level: 1, name: /legal/i })).toBeInTheDocument();
  });

  it("renders all six section headings", () => {
    renderLegal();
    const expected = [
      /trademark/i,
      /no affiliation/i,
      /purpose/i,
      /data source/i,
      /code/i,
      /contact/i,
    ];
    for (const name of expected) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
  });

  it("links to the GitHub repository", () => {
    renderLegal();
    const link = screen.getByRole("link", { name: /github\.com\/driversti\/formula1/i });
    expect(link).toHaveAttribute("href", "https://github.com/driversti/formula1");
  });

  it("links to the livetiming data source", () => {
    renderLegal();
    const link = screen.getByRole("link", { name: /livetiming\.formula1\.com/i });
    expect(link.getAttribute("href")).toContain("livetiming.formula1.com");
  });

  it("exposes the takedown contact as a mailto link", () => {
    renderLegal();
    const link = screen.getByRole("link", { name: /copyright@seniorjava\.dev/i });
    expect(link).toHaveAttribute("href", "mailto:copyright@seniorjava.dev");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from `site/`: `npm run test -- Legal`
Expected: FAIL (`Legal` module does not exist).

- [ ] **Step 3: Implement `Legal` route**

Create `site/src/routes/Legal.tsx`:

```tsx
export default function Legal() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-8 text-f1-text">
      <h1 className="mb-6 text-2xl font-bold tracking-wide">Legal</h1>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Trademark disclaimer</h2>
        <p className="text-sm text-f1-muted">
          "F1", "FORMULA 1", "FIA", the Formula 1 logo, all team names, driver names, and
          associated logos or marks are trademarks of their respective owners. This site makes
          no claim to any such marks.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">No affiliation</h2>
        <p className="text-sm text-f1-muted">
          This site is not affiliated with, endorsed by, sponsored by, or otherwise connected
          to Formula 1, the Fédération Internationale de l'Automobile (FIA), Formula One
          Management, or any Formula 1 team or driver.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Purpose</h2>
        <p className="text-sm text-f1-muted">
          This is a non-commercial, educational fan project for exploring Formula 1 timing
          data. It is provided as-is with no warranty of any kind.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Data source</h2>
        <p className="text-sm text-f1-muted">
          Timing data is sourced from{" "}
          <a
            href="https://livetiming.formula1.com/static/"
            className="text-f1-text underline hover:text-compound-soft"
            target="_blank"
            rel="noopener noreferrer"
          >
            livetiming.formula1.com/static/
          </a>
          . All rights to the underlying data belong to its owners.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Code</h2>
        <p className="text-sm text-f1-muted">
          The source code of this site is open source under the MIT license:{" "}
          <a
            href="https://github.com/driversti/formula1"
            className="text-f1-text underline hover:text-compound-soft"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/driversti/formula1
          </a>
          .
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">Contact and takedown requests</h2>
        <p className="text-sm text-f1-muted">
          For takedown requests or questions about this site, contact{" "}
          <a
            href="mailto:copyright@seniorjava.dev"
            className="text-f1-text underline hover:text-compound-soft"
          >
            copyright@seniorjava.dev
          </a>
          .
        </p>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run from `site/`: `npm run test -- Legal`
Expected: all five tests PASS.

- [ ] **Step 5: Commit**

```bash
git add site/src/routes/Legal.tsx site/tests/unit/Legal.test.tsx
git commit -m "feat(site): add /legal page with trademark disclaimer and attributions"
```

---

## Task 4: Wire footer into `AppShell` and register the `/legal` route

**Files:**
- Modify: `site/src/components/AppShell.tsx`
- Modify: `site/src/App.tsx`

- [ ] **Step 1: Mount the footer in `AppShell`**

Replace the contents of `site/src/components/AppShell.tsx` with:

```tsx
import { Outlet } from "react-router-dom";
import { SiteHeader } from "./SiteHeader";
import { SiteFooter } from "./SiteFooter";

export function AppShell() {
  return (
    <>
      <SiteHeader />
      <Outlet />
      <SiteFooter />
    </>
  );
}
```

- [ ] **Step 2: Register the `/legal` route**

Edit `site/src/App.tsx`:

1. Add an import after the existing route imports:

```tsx
import Legal from "./routes/Legal";
```

2. Add this route inside the `children` array of the `AppShell` route, directly above the catch-all `{ path: "*", element: <NotFound /> }`:

```tsx
        { path: "/legal", element: <Legal /> },
```

- [ ] **Step 3: Build + unit tests**

Run from `site/`:

```bash
npm run build
npm run test
```

Expected: `tsc -b` + `vite build` succeed; all Vitest tests pass including the new SiteFooter, Legal, and breadcrumbs cases.

- [ ] **Step 4: Commit**

```bash
git add site/src/components/AppShell.tsx site/src/App.tsx
git commit -m "feat(site): mount SiteFooter in AppShell and register /legal route"
```

---

## Task 5: E2E coverage

**Files:**
- Create: `site/tests/e2e/legal.spec.ts`

- [ ] **Step 1: Write the failing E2E test**

Create `site/tests/e2e/legal.spec.ts`:

```ts
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
```

- [ ] **Step 2: Run the E2E suite**

From the repo root (stages the manifest automatically):

```bash
make test-e2e
```

If Playwright browsers are not yet installed: `cd site && npx playwright install --with-deps chromium` first.

Expected: all E2E tests PASS, including the two new ones in `legal.spec.ts`.

- [ ] **Step 3: Full test suite**

From the repo root:

```bash
make test
```

Expected: Python tests + site unit tests + Playwright E2E all PASS. Coverage gates hold (Python ≥85%, site ≥80% lines).

- [ ] **Step 4: Commit**

```bash
git add site/tests/e2e/legal.spec.ts
git commit -m "test(site): add E2E coverage for /legal page and footer link"
```

---

## Done criteria

- Every page renders a muted footer with the disclaimer and a working `Read more` link.
- `/legal` renders all six sections with the specified attribution links and `mailto:copyright@seniorjava.dev`.
- Breadcrumb on `/legal` reads `Home / Legal`.
- `make test` passes end-to-end.
