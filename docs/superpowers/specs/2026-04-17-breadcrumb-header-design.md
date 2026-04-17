# Breadcrumb Header — Design Spec

**Date:** 2026-04-17
**Branch:** `feature/breadcrumb-header`
**Status:** Approved for planning

## Goal

Give users a persistent way to orient themselves in the site's season → race → analytics hierarchy and to navigate up that hierarchy in one click, from any page.

## User Story

> As a user, I want to see a header with breadcrumbs so I can easily navigate between seasons and races — choosing the main page, any season, any race, or any analytics for a quick overview.

## Scope

- Add a persistent, sticky site header across every route.
- Header shows a brand mark on the left and a plain breadcrumb trail on the right.
- Breadcrumbs are plain links (no dropdown selectors).
- No changes to routing, data loading, or existing in-page headers.

## Non-goals (YAGNI)

- Dropdowns / sideways season or race pickers.
- Keyboard shortcuts beyond browser defaults.
- Responsive label shortening — narrow viewports use horizontal scroll instead.
- Analytics / telemetry for nav clicks.

## Route model

Existing routes (from `site/src/App.tsx`):

| Pathname | Page |
|---|---|
| `/` | Seasons index |
| `/season/:year` | Season (list of races) |
| `/race/:slug` | Race (analytics index) |
| `/race/:slug/tyres` | Tyre inventory |
| `/race/:slug/driver/:tla` | Driver detail |
| `*` | NotFound |

## Trail derivation

`useBreadcrumbs(pathname)` matches against these patterns and returns an ordered `{label, href, current}[]`:

| Pathname | Trail |
|---|---|
| `/` | `[Home*]` |
| `/season/:year` | `Home › 2026*` |
| `/race/:slug` | `Home › 2026 › Australian GP*` |
| `/race/:slug/tyres` | `Home › 2026 › Australian GP › Tyres*` |
| `/race/:slug/driver/:tla` | `Home › 2026 › Australian GP › Driver · VER*` |
| unknown path | `[Home*]` |

(`*` = current, rendered as non-link text with `aria-current="page"`.)

Rules:
- Year and race name come from `SCHEDULE` (`site/src/data/schedule.ts`), same lookup `Race.tsx` already does.
- Race label: `"<CountryName> GP"` when the official race name ends in `"Grand Prix"`, otherwise `race.name` verbatim (covers special cases like "70th Anniversary Grand Prix").
- If a slug is not in `SCHEDULE`, the trail stops at the last known segment; the route itself will render `NotFound`.

## Architecture

```
<App>
  <AppShell>          ← layout route; sticky header + <Outlet />
    <SiteHeader>
      <Brand />       ← links to /
      <Breadcrumbs /> ← derives trail from useLocation()
    </SiteHeader>
    <Outlet />        ← existing Seasons / Season / Race / Tyres / Driver / NotFound
  </AppShell>
</App>
```

The existing routes become children of a layout route. Page components keep their own in-page `<header>` (kicker + title); the site header is additive.

## Components

| File | Responsibility |
|---|---|
| `site/src/components/AppShell.tsx` | Sticky header wrapper + `<Outlet />`. No props. |
| `site/src/components/SiteHeader.tsx` | `<header>` with `<Brand>` left, `<Breadcrumbs>` right. Owns layout/styling of the bar. |
| `site/src/components/Breadcrumbs.tsx` | `<nav aria-label="Breadcrumb">` with ordered list from `useBreadcrumbs()`. Renders links + current item. |
| `site/src/lib/breadcrumbs.ts` | Pure `buildTrail(pathname, schedule)` function + `useBreadcrumbs()` hook that wires it to `useLocation()`. |

## Styling & behavior

- **Bar:** `sticky top-0 z-20 bg-f1-panel border-b border-f1-border px-5 py-3` · flex row · `items-center justify-between`.
- **Brand (left):** small red square (`bg-compound-soft`) + `F1 DASHBOARD` wordmark · `text-sm font-bold tracking-wide` · links to `/`.
- **Crumbs (right):** `text-sm text-f1-muted`. Links: `text-f1-text hover:bg-white/5 rounded px-1.5 py-0.5`. Separator `›` in `text-f1-border`. Current: `text-f1-accent` with `aria-current="page"` (not a link).
- **Overflow:** breadcrumb container is `overflow-x-auto whitespace-nowrap`, scrollbar hidden (`::-webkit-scrollbar{display:none}`, `scrollbar-width:none`). Crumbs shrink-to-fit; the bar itself never wraps.
- **In-page content:** route components keep `<main className="mx-auto max-w-6xl p-6">` unchanged. No top-padding tweaks required.

## Accessibility

- `<nav aria-label="Breadcrumb">` wraps the list.
- Ordered list (`<ol>`) with list items (`<li>`).
- Current page uses `aria-current="page"` and is rendered as text, not a link.
- Separators (`›`) are decorative (`aria-hidden="true"`).
- Links use React Router `<Link>` (keyboard/focus handled natively).

## Testing

- **Unit (vitest):** `site/src/lib/breadcrumbs.test.ts` — covers every pathname pattern above, including unknown slug, unknown year, and the NotFound fallback.
- **Component (vitest + RTL):** `site/src/components/Breadcrumbs.test.tsx` — verifies current item has `aria-current="page"`, non-current items are links with expected `href`, and `aria-label="Breadcrumb"` is present.
- **E2E (Playwright):** one spec walks `/` → 2026 season → a race → Tyres, then uses the header breadcrumbs to jump back to `2026` and to `Home`, asserting the URL at each hop. Covers the core user story.

## Files changed

- **New:** `AppShell.tsx`, `SiteHeader.tsx`, `Breadcrumbs.tsx`, `lib/breadcrumbs.ts`, `lib/breadcrumbs.test.ts`, `components/Breadcrumbs.test.tsx`, one new Playwright spec.
- **Modified:** `site/src/App.tsx` (wrap existing routes in a layout route that renders `<AppShell>`).
- **Untouched:** all existing route components, `schedule.ts`, data loading, Zod/Pydantic schemas, the precompute pipeline.

## Open questions

None — all design decisions resolved during brainstorming (Q1–Q5: plain links; persistent bar on every route; compact labels with explicit leaf type; sticky on scroll; horizontal scroll on narrow viewports).
