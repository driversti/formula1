# Legal Page & Site Footer — Design

**Date:** 2026-04-17
**Status:** Approved — ready for implementation plan

## Motivation

The site displays Formula 1 data, driver names, team names, and related identifiers that are trademarks of their respective owners. To avoid any implied claim of ownership, endorsement, or affiliation, the site needs a visible disclaimer on every page and a dedicated legal page spelling out trademark ownership, data sourcing, and contact information for takedown requests.

## Scope

- Add a site-wide footer with a short disclaimer and a link to a full legal page.
- Add a `/legal` route rendering a static legal/disclaimer page.
- Update breadcrumb navigation to recognise the legal page.
- Unit and E2E tests for both.

Out of scope: privacy policy, cookie banner, analytics opt-out (the site has no analytics or cookies).

## Components

### 1. `SiteFooter` component

- **Path:** `site/src/components/SiteFooter.tsx`
- **Purpose:** Render a muted, single-line disclaimer below page content on every route.
- **Content:** *"Unofficial fan site. All trademarks belong to their respective owners."* followed by a `Read more` link to `/legal`.
- **Styling:** Tailwind, muted text tone consistent with existing `SiteHeader`. No heavy borders; matches existing aesthetic.
- **Integration:** Rendered inside `AppShell` (`site/src/components/AppShell.tsx`) below the main content outlet, so every route inherits it.

### 2. `Legal` route

- **Path:** `site/src/routes/Legal.tsx`
- **URL:** `/legal`
- **Registration:** Added to the router in `site/src/App.tsx`.
- **Data:** None — static content only. No manifest loading, no Zod validation.
- **Sections (H2 per section):**
  1. **Trademark disclaimer** — "F1®", "FORMULA 1", "FIA", all team names, driver names, and associated logos/marks are trademarks of their respective owners. This site makes no claim to any such marks.
  2. **No affiliation** — The site is not affiliated with, endorsed by, or connected to Formula 1, the Fédération Internationale de l'Automobile (FIA), Formula One Management, or any Formula 1 team or driver.
  3. **Purpose** — A non-commercial, educational fan project for exploring F1 timing data.
  4. **Data source** — Timing data is sourced from `livetiming.formula1.com/static/` (link rendered). All rights to the underlying data belong to its owners.
  5. **Code** — The site's source code is open source under the MIT license. Link to `https://github.com/driversti/formula1`.
  6. **Contact / takedown** — Contact `copyright@seniorjava.dev` with takedown requests or questions (rendered as a `mailto:` link).

### 3. Breadcrumbs

- **File:** `site/src/components/Breadcrumbs.tsx` (update)
- Add a recognised entry for `/legal` so the breadcrumb trail reads `Home / Legal` on that page.

## Routing

Add to `site/src/App.tsx`:

```tsx
<Route path="/legal" element={<Legal />} />
```

Accessible from every page via the footer link. Not linked from the main nav — it's a legal document, not a primary destination.

## Testing

### Unit (Vitest)

- **`site/src/routes/__tests__/Legal.test.tsx`** — render `<Legal />` and assert:
  - All six section headings present.
  - `copyright@seniorjava.dev` rendered as a `mailto:` link.
  - GitHub repo URL present as a link.
  - `livetiming.formula1.com` attribution present.
- **`site/src/components/__tests__/SiteFooter.test.tsx`** — render `<SiteFooter />` and assert:
  - Disclaimer text is present.
  - `Read more` link points to `/legal`.

### E2E (Playwright)

- **`site/tests/e2e/legal.spec.ts`:**
  - From home, the footer link navigates to `/legal`.
  - Legal page shows all section headings.
  - Breadcrumb reads `Home / Legal`.
  - Contact email and GitHub links are present and well-formed.

## File checklist

**New:**
- `site/src/components/SiteFooter.tsx`
- `site/src/components/__tests__/SiteFooter.test.tsx`
- `site/src/routes/Legal.tsx`
- `site/src/routes/__tests__/Legal.test.tsx`
- `site/tests/e2e/legal.spec.ts`

**Modified:**
- `site/src/components/AppShell.tsx` — mount `SiteFooter`.
- `site/src/components/Breadcrumbs.tsx` — recognise `/legal`.
- `site/src/App.tsx` — register `/legal` route.

## Non-goals / YAGNI

- No CMS, no Markdown loader — plain JSX is fine for a single static page.
- No i18n — the site is English-only today.
- No separate privacy/terms pages — out of scope until the site collects data.
